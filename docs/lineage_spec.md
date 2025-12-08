# `docs/lineage_spec.md`

```
# Lineage Event Specification (Draft)

Cold Root Identity introduces an offline root key and a rotating set of deterministic
epoch keys. A lineage event is the cryptographic proof that binds an epoch key to its
cold root authority. This allows clients to follow identity rotation safely without any
protocol changes.

This document defines the canonical lineage event format, verification rules, and client
expectations.

---

## 1. Purpose

A lineage event proves:

1. The epoch key was derived from the correct cold root.
2. The epoch key is the currently valid operational key for a given epoch label.
3. The root key never touches a live client or networked device.

Clients use lineage events to follow root → epoch continuity and automatically rotate
identities when a newer epoch key appears.

---

## 2. Event Kind

Recommended event kind for lineage proofs:

```

30001

````

This is not mandatory, but clients should treat 30001 as the default discovery channel.

---

## 3. Required Event Structure

### Minimal valid lineage event

```json
{
  "kind": 30001,
  "pubkey": "<epoch_pubkey_hex>",
  "created_at": 1733660000,
  "tags": [
    ["root", "<root_pubkey_hex>"],
    ["sig", "<signature_over_raw_epoch_pubkey_hex>"],
    ["epoch", "2025Q1"]
  ],
  "content": ""
}
````

### Field Requirements

* **pubkey**
  Must be the *raw 32-byte hexadecimal* epoch public key.
  Not Bech32. Not npub. No wrapping.

* **root tag**
  Must contain the raw hex encoding of the root public key.

* **sig tag**
  Must contain an ed25519 signature produced by the *cold root* over the unencoded
  epoch public key bytes.

* **epoch tag**
  Human readable label for the epoch namespace (e.g. `2025Q1`, `2026-01`, `v2`).

* **content**
  Always empty. No metadata goes here.

---

## 4. Signature Rule

The signature must be computed as:

```
sig = Sign(root_private_key, epoch_pubkey_bytes)
```

Where:

* `epoch_pubkey_bytes` is the raw 32-byte ed25519 public key
* The encoding of the signature is **raw hex**

There must be **no hashing, no wrappers, and no event envelope** around the signed data.
The root signs only the epoch public key.

---

## 5. Verification Algorithm (Client-Side)

Given a lineage event `E`:

1. Extract:

   * `epoch_pubkey` (hex → bytes)
   * `root_pubkey` (hex → bytes from `["root"]`)
   * `signature` (hex → bytes from `["sig"]`)
2. Use ed25519 verification:

   ```
   Verify(root_pubkey, signature, epoch_pubkey)
   ```
3. If verification fails → reject the lineage event.
4. If multiple lineage events exist for the same root:

   * Prefer the newest `created_at`
   * If timestamps conflict, use the newest epoch label (string compare or client-defined precedence)
   * If lineage is ambiguous or conflicting → require user confirmation.

---

## 6. Client Expectations

### 6.1 Root Key Handling

The cold root key:

* Never posts events
* Never appears in any Nostr client
* Never resides on a networked device

Clients should never treat the root pubkey as a posting identity.

### 6.2 Epoch Key Lifecycle

Clients should:

* Accept an epoch key only after a valid lineage event is discovered.
* Follow new epoch keys when:

  * The root pubkey matches the existing one
  * The signature verifies
  * The epoch label appears newer (per client policy)

### 6.3 Compromise Containment

If an epoch key is compromised:

* Only that epoch interval is exposed
* Identity continuity remains intact because the root stays offline

Clients should highlight when a lineage event appears late or out of order.

---

## 7. Failure Modes

### Missing lineage

Client MUST reject an epoch key that is not accompanied by a valid lineage event.

### Invalid signature

Client MUST reject immediately.

### Conflicting lineage

Client SHOULD warn the user and not switch keys automatically.

### Epoch event from wrong root

Client MUST reject.

---

## 8. Rationale

The lineage event format:

* Uses standard NIP-01 JSON
* Requires no relay changes
* Requires no protocol extensions
* Works today in all clients
* Provides cryptographic continuity for long-lived identities

This keeps Nostr simple while enabling safe operational key rotation.

---

## 9. Status

This is a **draft specification** and may evolve as client developers provide feedback.


