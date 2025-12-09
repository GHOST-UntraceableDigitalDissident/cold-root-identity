# Cold Root Identity Specification

```
NIP:      CRI-01
Title:    Cold Root Identity
Author:   GHOST (Untraceable Digital Dissident)
Status:   Draft
Version:  v0.1.0
Created:  2025-12-09
License:  Permissive
```




Cold Root Identity defines a deterministic key rotation scheme that preserves long term identity continuity on Nostr. An offline root key authorizes each new epoch key through a signed lineage event. Clients that follow lineage gain survivable identity with no protocol changes and no relay modifications.

## 1. Terminology

### Root key
A 32 byte seed stored offline permanently. The only authority for the identity.

### Epoch key
A derived ed25519 keypair used as the active posting key for a specific time window. The private seed is derived deterministically but the private key itself is never included in lineage, only the public.

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

### 2.2 HKDF Parameters

Derivation uses HKDF SHA256 with fixed parameters:

```
KDF: HKDF-SHA256
Salt: "nostr-cold-root" (ASCII)
Info: "epoch:<epoch_label>" (ASCII)
L: 32 bytes
```
Salt MUST remain constant for all CRI implementations.
Not required, but strengthens cross-compatibility.

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

If any step fails, lineage MUST be rejected.

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

## 6. Security Model (Short)

• Root key MUST remain offline  
• Epoch keys SHOULD rotate regularly  
• Compromise of an epoch key is contained to its epoch window  
• Missing lineage SHOULD trigger warnings  
• Lineage SHOULD be published immediately after loading a new epoch key  
• Compromise of the root key invalidates the full identity

## 7. Compatibility and Non Breaking Behavior

Cold Root Identity is fully backward compatible.

• No relay changes  
• No NIP changes  
• No protocol level additions  

Non aware clients treat epoch keys as ordinary Nostr keys.  
Aware clients gain survivable identity and forward secure rotation.

There are no interoperability risks.

## 8. Reference Implementations

Canonical reference materials:

• `cold_root_identity.py`  
• `test_vectors/epoch_derivation.json`  
• `test_vectors/lineage_events.json`

Implementations SHOULD match all reference vectors exactly.

## 9. License

The Cold Root Identity specification is released under a permissive license to maximize adoption, cross client compatibility, and independent reimplementation.
