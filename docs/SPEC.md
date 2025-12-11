# Cold Root Identity Specification

```
NIP:      CRI-01
Title:    Cold Root Identity
Author:   GHOST (Untraceable Digital Dissident)
Status:   Draft
Version:  v0.1.0
Created:  2025-12-09
License:  MIT
```




Cold Root Identity defines a deterministic key rotation scheme that preserves long term identity continuity on Nostr. An offline root key authorizes each new epoch key through a signed lineage event. Clients that follow lineage gain survivable identity with no protocol changes and no relay modifications.

SPEC.md is normative; other docs are explanatory breakdowns of sections 2–6” and avoid introducing new MUST/SHOULD rules outside SPEC.

## 1. Terminology

### Root key
A 32 byte seed stored offline permanently. The only authority for the identity.

### Epoch key
A derived ed25519 keypair used as the active posting key for a specific time window. The private seed is derived deterministically but the private key itself is never included in lineage, only the public.

### Epoch 0   
A user’s existing Nostr key authenticated by the new root key; it anchors history but never acts as a seed or authority for future epochs.

### Epoch label
A UTF 8 string used as the derivation namespace. Labels MUST be treated as raw byte strings without normalization.  
Examples: `2025Q4`, `2026-01`, `2026-01-01`, `v2`, `compromise-001`.

### Lineage event
A NIP 01 event signed by the root key proving that an epoch key descends from it.

### Active epoch
The newest valid epoch key determined by lineage verification.

## 2. Derivation Scheme

Cold Root Identity requires deterministic epoch key derivation across all implementations.

### 2.1 Inputs

Implementations MUST accept:

**root_seed**  
• Exactly 32 raw bytes  
• External encoding MAY be hex  
• MUST NOT exceed 32 bytes

**epoch_label**  
• UTF 8 string  
• MUST NOT be modified in any way  
• Reuse yields identical keys

### Epoch Label Format

Epoch keys MUST be derived from a unique, deterministic label. The label MUST be a UTF8 string and MUST NOT repeat for the same root authority. Labels MAY be human readable or structured, but they MUST satisfy all of the following:  
- The label uniquely identifies a single epoch.  
- The label is stable under re derivation.  
- The label does not encode secret material.  
- The label is included verbatim in lineage events so that clients can reproduce and verify derivation.  

Common examples include sequential integers (“0”, “1”, “2”, …) or structured time based labels (“2025Q4”, “2026Q1”), but the specification only requires uniqueness and determinism. 

Implementations MUST treat reuse of a label for the same root authority as an error.

### 2.2 HKDF Parameters

Derivation uses HKDF SHA256 with fixed parameters:

```
KDF: HKDF-SHA256
Salt: "nostr-cold-root" (ASCII)
Info: "epoch:<epoch_label>" (ASCII)
L: 32 bytes
```
Salt MUST remain constant for all CRI implementations.


### 2.3 Key Material

Implementations MUST:

• Use the 32 byte HKDF output as the ed25519 private seed  
• Apply standard ed25519 clamping  
• Compute the public key via standard ed25519 scalar multiplication  

Encoding rules:  
• Internal: raw 32 bytes  
• For the spec: hex  
• UI encodings (npub/nsec) are OPTIONAL

### 2.4 Determinism Requirements

• Identical `(root_seed, epoch_label)` MUST produce identical epoch keypairs  
• Different labels MUST produce distinct keypairs  
• Labels MUST NOT be normalized, trimmed, transformed, or lowercased  
• These determinism requirements apply uniformly across all reference
implementations, including Python, Go, and JavaScript.


## 3. Lineage Event Format

### 3.1 Recommended Event Kind

```
kind: 30001
```

### 3.2 Required Event Fields

A lineage event MUST contain:

**pubkey**  
Hex encoded epoch public key (32 bytes). MUST NOT be npub.

**created_at**  
Standard NIP 01 timestamp.

**tags**  
MUST include:
```
["root", "<root_pubkey_hex>"]
["sig", "<hex_signature_by_root_over_epoch_pubkey_raw_bytes>"]
["epoch", "<epoch_label>"]
```


Additional tags MAY be included but MUST NOT affect verification.

**content**  
MUST be the empty string `""`.

### 3.3 Signing Rules

The root key MUST sign:
```
Message: raw 32 byte epoch public key
Algorithm: ed25519
Signature: 64 byte raw signature, hex encoded
```

No hashing, prefixing, or alternative message formats are allowed.  
If the signature covers anything other than the raw epoch pubkey bytes, verification MUST fail.

## 4. Verification Rules

Given `(root_pubkey, lineage_event)` a client MUST:

1. Validate `lineage_event.kind == 30001`
2. Confirm a `["root", X]` tag exists and `X == root_pubkey`
3. Hex decode `pubkey` into raw `epoch_pubkey` bytes
4. Hex decode the signature from `["sig", S]`
5. Verify:
```
ed25519_verify(
public_key = root_pubkey,
message = epoch_pubkey_raw,
signature = S
)
```

6. Extract the epoch label from the `["epoch", label]` tag

### 4.2 Freshness and Non Reuse

Clients MUST reject any lineage event where the `epoch_pubkey` in the event has already appeared earlier in the same root authority’s lineage chain.

### 4.3 Epoch Label Validation

After extracting the label, a client MUST ensure:
- The label is a UTF8 string.  
- The label has not appeared earlier in the lineage for this root.  
- The label exactly matches the value carried in the lineage event and MUST NOT repeat for this root.    
- The label is stable under re derivation and uniquely identifies this epoch.  
- If any label validation fails, the lineage event MUST be rejected.  

If any step fails, lineage MUST be rejected.

### 4.4 Migration for Existing Long Lived Keys

Existing Nostr identities that were not originally derived from a CRI root key MUST be treated as `epoch 0`. Epoch 0 represents the first operational key in the lineage, but it is not a derivation parent for any future epochs.  

#### Migration proceeds as follows:  
1. The user generates a new offline root key.
2. The user publishes a lineage event binding the root key to their existing pubkey, designating it as `epoch 0`.  
3. Clients that support CRI MUST accept this lineage event as the authoritative starting point for the identity.  
4. **All future epoch keys are derived deterministically from the root key**, not from `epoch 0`.  
5. Epoch 0 behaves exactly like any other epoch: it remains valid for historical events, but it never acts as a seed or derivation input.  

This rule preserves CRI’s core security property: **only the root key may authorize forward motion in the identity**.  
Operational keys, including epoch 0, cannot derive or authorize future epochs. Using the existing hot key as a derivation seed destroys the cold root guarantee.

### 4.5 Identity Anchoring for Migration

When migrating an existing long lived Nostr key into CRI, the existing identity MUST anchor the root binding.

Clients implementing CRI MUST apply the following rules:
1. Existing key must publish the binding  
  A lineage event that introduces a root key for an existing identity MUST be signed by that identity’s current operational key `epoch 0` and MUST appear in that key’s event history.  

2. Third-party bindings are ignored  
  A lineage event that binds a root key to some pubkey, but is signed by any other key, MUST NOT be treated as a valid migration or root binding for that identity.

3. No replacement without the identity’s own signature  
  Clients MUST NOT replace or extend an identity’s lineage based solely on a newly introduced root key. The existing key MUST explicitly accept the root via a lineage event.

Clients MUST associate lineage events with the identity that created the event, not with the pubkey referenced inside the event’s tags.  

#### Security rationale

This preserves the core security property that the identity accepts the root, not the other way around. An attacker cannot steal an identity by generating a new root and publishing a lineage event that “claims” someone else’s pubkey, because they cannot get that lineage event into the victim’s event feed without the victim’s private key. The only way to hijack an identity under CRI is to already possess the victim’s original nsec, which is the same precondition required to hijack the identity in today’s Nostr model. CRI does not weaken this; it only limits the blast radius once rotation occurs.

## 5. Client Behavior Summary

Clients implementing Cold Root Identity MUST:

• Locate all lineage events referencing the root pubkey.  
• Verify lineage signatures.  
• Clients MUST reject lineage events where the pubkey in the event does not match the key used to sign the lineage event object itself.  
• Clients MUST NOT synthesize lineage events; they may only follow lineage published and signed by the root key.  
• Sort valid lineage events by:  
  - Primary: `created_at` descending  
  - Secondary: client defined tie breaking
    
• Treat the newest valid lineage as the active epoch  


Use the active epoch key for:

• identity display  
• posting  
• metadata updates  

### Conflict Handling

If lineage events conflict (invalid signatures, mismatched roots, contradictory epochs):

• Clients MUST NOT auto rotate  
• Clients MUST show a warning  
• Clients MAY require explicit user selection

## 6. Client Integration

Clients implementing Cold Root Identity MUST follow the behaviors in this section. These rules define how lineage is discovered, validated, selected, and applied, and how client behavior changes when lineage is absent, invalid, or ignored.

### 6.1 Discovery of Lineage Events

A client MUST attempt to discover lineage events for a known root authority. Discovery MAY use any of the following mechanisms:

• Querying relays for events of kind: 30001 signed by the root pubkey  
• Following a user provided root pubkey declared in metadata  
• Using cached lineage previously verified by the client  

Clients MUST NOT infer or synthesize lineage. Only published events signed by the root are valid sources of truth.  

### 6.2 Freshness Selection Rule

When multiple valid lineage events exist for the same root authority, clients MUST select the freshest valid epoch. Freshness is defined strictly by:
1. Highest `created_at` timestamp  
2. If two lineage events share the same timestamp, the client MAY apply implementation specific tie breaking (e.g., event id ordering)  

The lineage event with the highest **valid** `created_at` becomes the active epoch for all signing and display behavior.  

### 6.3 Handling Missing or Invalid Lineage

When clients fail to locate any valid lineage for a given root pubkey:

• The client MUST treat the origin root key as the identity anchor  
• The client MUST show a warning if the user attempts to post  
• The client MUST NOT guess an epoch key or rotate implicitly  

When lineage exists but is invalid (failed signature, mismatched root, reused label, reused epoch pubkey):

• The client MUST ignore the invalid lineage event  
• The client MUST NOT switch epochs  
• The client MAY surface a warning to the user  

### 6.4 Continuity of Historical Events

Clients MUST preserve event continuity:

• Events signed under old epoch keys MUST remain attributed to those epoch keys  
• Clients MUST NOT rewrite, remap, or reinterpret signatures from previous epochs  
• History continuity MUST be computed strictly by the pubkey used at the time the event was created  

Lineage does not retroactively re sign or re anchor older events. Continuity is preserved by design.

### 6.5 Switching Active Signing Keys

After verifying lineage and selecting the freshest valid event:
1. Extract the epoch public key   
2. Verify the root signature over the raw epoch pubkey bytes  
3. If valid, adopt that epoch pubkey as the current active identity  
4. When posting, the client MUST sign with the user’s corresponding epoch private key (imported or generated deterministically by the user’s local implementation)  

Clients MUST NOT switch keys unless lineage verification succeeds.

### 6.6 Ignoring Lineage

Clients MAY choose to ignore lineage entirely. This is allowed behavior and preserves backward compatibility.

However:

• Ignoring lineage results in **identity discontinuity**  
• Users interacting through such clients will appear to “change pubkeys” when entering a new epoch  
• Clients MUST NOT present ignored lineage as erroneous; it is simply unsupported  

### 6.7 Minimal Compliance Summary

A client supporting Cold Root Identity MUST:

• Discover lineage events for a given root  
• Verify the root signature over the epoch pubkey  
• Reject reused epoch labels or reused epoch keys  
• Select the freshest valid lineage event  
• Adopt the associated epoch key as the active identity  
• Preserve historical attribution to older epoch pubkeys  
• Treat missing or invalid lineage conservatively and never rotate implicitly  

## 7. Security Model (Short)

• Root key MUST remain offline  
• Epoch keys SHOULD rotate regularly  
• Compromise of an epoch key is contained to its epoch window  
• Missing lineage SHOULD trigger warnings  
• Lineage SHOULD be published immediately after loading a new epoch key  
• Compromise of the root key invalidates the full identity

## 8. Compatibility and Non Breaking Behavior

Cold Root Identity is fully backward compatible.

• No relay changes  
• No NIP changes  
• No protocol level additions  

Non aware clients treat epoch keys as ordinary Nostr keys.  
Aware clients gain survivable identity and forward secure rotation.

There are no interoperability risks.

## 9. Reference Implementations

Reference vectors SHALL be located at `tests/vectors/cold_root_identity.v1.json`  

Implementations MUST match all reference vectors exactly to claim CRI-01
compliance.

As of tag `v0.1.0-vectors`, three reference implementations reproduce the
vectors byte-for-byte:  

- **Python** (`coldroot/`)  
- **Go** (`go/`)  
- **JavaScript (Node)** (`js/`)  

Any implementation in any language MUST reproduce the values in
`tests/vectors/cold_root_identity.v1.json` exactly.

## 10. Reference Vectors (Normative)

Implementations of Cold Root Identity must reproduce the official reference vectors published with this specification.  
The canonical root seed for test purposes is:

`000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f`  

From this seed, implementations must deterministically derive:  
1. The root secret key and public key  
2. The epoch secret key and public key for the label `"2025-Q1"`   
3. The lineage event binding the root to the `"2025-Q1"` epoch key  

The authoritative vectors are stored in the repository under:  

`tests/vectors/cold_root_identity.v1.json`

A deterministic timestamp scheme is used for reference vectors:  
epoch labels of the form `"YYYY-Qn"` map to the first second of that quarter in UTC.  
Runtime clients remain free to use the current time for freshness.

A signed Git tag identifies the vector freeze:

`v0.1.0-vectors`

Any change to derivation rules or lineage semantics MUST be accompanied by new reference vectors and a new versioned tag.

### HKDF derivation parameters (normative)

Epoch keys are derived from the 32 byte root seed using HKDF-SHA256 with the
following exact parameter set:
```
IKM = root_seed (32 bytes, decoded from hex)    
salt = "nostr-cold-root" (UTF-8)  
info = "epoch:" + label (UTF-8)    
length = 32 bytes
```  

Implementations MUST use these parameters to reproduce the reference vectors in
`tests/vectors/cold_root_identity.v1.json`

### Matching Implementations

As of tag `v0.1.0-vectors`, Python, Go, and JavaScript all reproduce the vectors exactly  

Any future implementation must reproduce the values in
`tests/vectors/cold_root_identity.v1.json` byte-for-byte to claim compliance
with this specification.

### JavaScript Determinism

The JavaScript reference implementation (`js/`) uses TweetNaCl for Ed25519 and
a native HKDF-SHA256 implementation. It reproduces all vector fields exactly,
including: 

- epoch secret key and public key  
- root signature over raw epoch public key bytes  
- lineage event structure and field ordering  
- deterministic timestamp mapping for labeled epochs  

Any future JavaScript or TypeScript implementation MUST match these values
exactly.


### Compliance Requirement

To claim compatibility with this specification, an implementation MUST:  
- Re-derive all keys and lineage fields from the canonical seed
- Match the reference JSON exactly for:
  - sk_hex
  - pk_hex
  - kind
  - created_at
  - tags
  - pubkey
- Pass the same vector tests provided in `tests/test_vectors.py`

Failure to reproduce these vectors indicates a deviation from the specification.

## 11. License

The Cold Root Identity specification is released under a MIT license to maximize adoption, cross client compatibility, and independent reimplementation.
