# Client Integration Guidance (Draft)

This document describes how Nostr clients can support Cold Root Identity without any
protocol changes or additional NIPs. All verification happens locally using standard
NIP-01 events and ed25519 signatures.

The goal is to allow clients to automatically follow identity rotation, validate lineage
proofs, and maintain continuity even if an epoch key is compromised.

---

## 1. Overview

Cold Root Identity defines:

- A *cold root key* that never touches a live device
- Deterministic *epoch keys* derived from the root
- A *lineage event* proving the epoch key was authorized by the root

Clients operate entirely on epoch keys. The root key is never used for posting and never
imported into software clients.

---

## 2. What Clients Must Support

Clients need to implement only three behaviors:

1. **Discover lineage events**
2. **Verify lineage signatures**
3. **Follow the newest valid epoch key**

No relay behavior changes. No new protocol primitives.

---

## 3. Discovering Lineage Events

Clients SHOULD search for lineage events using:

### A. Event kind (recommended)

```

kind = 30001

```

This is the canonical lineage channel.

### B. Tags in metadata (optional)

Clients MAY also recognize:

```

["root", <root_pubkey_hex>]
["epoch", <label>]

````

Use of metadata is optional, but recommended for UX.

### C. Explicit search by root key

If the user supplies the root public key (safe to share), the client can query:

- events of kind 30001 containing `["root", <root_pubkey>]`

This allows instant lineage resolution.

---

## 4. Verifying Lineage

Given a lineage event:

```json
{
  "kind": 30001,
  "pubkey": "<epoch_pubkey_hex>",
  "tags": [
    ["root", "<root_pubkey_hex>"],
    ["sig", "<signature_hex>"],
    ["epoch", "<label>"]
  ]
}
````

Clients MUST:

1. Decode:

   * `epoch_pubkey_hex` → raw 32 bytes
   * `root_pubkey_hex` → raw 32 bytes
   * `signature_hex` → raw 64 bytes

2. Verify signature:

```
ed25519_verify(
    root_pubkey,
    signature,
    epoch_pubkey
)
```

3. If verification fails → reject the epoch key and notify the user.

4. If verification passes → client may treat the epoch key as a valid posting identity.

---

## 5. Rotation Rules

Clients SHOULD automatically switch to the newest epoch key when:

* The lineage event verifies successfully
* The epoch label is newer than the currently active one
  (string comparison or client-defined policy)
* The timestamp `created_at` is newer than the last lineage event

The root pubkey must always match the previously validated one.

---

## 6. Handling Multiple Epoch Keys

Clients MUST follow these rules when multiple valid lineage events exist:

### Rule 1 — Prefer the newest `created_at`

A higher timestamp indicates a newer epoch key.

### Rule 2 — If timestamps tie, prefer newer epoch label

Example:

* 2025Q1
* 2025Q2
* 2026Q1

### Rule 3 — Never auto-switch when lineage conflicts

If two lineage events have:

* Different roots, or
* Different signatures for the same epoch pubkey,

the client MUST halt automatic rotation and warn the user.

---

## 7. Entering the Root Pubkey

Users SHOULD NEVER import their root private key.

Clients SHOULD allow users to input:

* The root **public** key (safe)
* Or an npub representing the root (optional)
* Or let the client extract the root from the most recent lineage event

The root public key is used only to verify lineage, never to sign.

---

## 8. Security Considerations

### 8.1 Root key compromise

If a root key is compromised, the attacker can mint unlimited valid epoch keys.
Clients SHOULD warn if:

* Too many lineage events appear in a short window
* Epoch labels regress (e.g., suddenly `2022Q4` appears)

### 8.2 Epoch key compromise

If an epoch key is compromised:

* Only that epoch window is exposed
* The next derived epoch key restores full security

Clients SHOULD warn when an epoch key publishes an unexpected large volume of events.

### 8.3 Missing lineage

Clients MUST reject any epoch key that does not have a valid lineage event.

### 8.4 Delayed lineage publication

If an epoch key appears without lineage for too long, clients SHOULD prompt:

```
"This key has no lineage proof yet. Trust anyway?"
```

User interaction required.

---

## 9. UX Recommendations

Clients SHOULD:

* Display the current epoch label and root pubkey
* Allow users to manually force rotation (e.g., “switch to 2026Q1”)
* Highlight lineage failures prominently
* Provide a “verify continuity” button that runs validation manually

This encourages users to adopt safer long-term identities without extra complexity.

---

## 10. Integration Notes for Developers

Implementing Cold Root Identity requires only:

* ed25519 signature verification
* standard NIP-01 event parsing
* a simple lineage lookup

No new dependencies or relay-side logic are required.

Clients may optionally:

* Cache lineage events locally
* Sync lineage validity across devices
* Support previews for future scheduled epoch keys

---

## 11. Status

This document is part of the Cold Root Identity draft specification and will evolve
as Nostr client developers provide feedback and interoperability testing results.


