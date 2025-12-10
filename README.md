# **Cold Root Identity (CLI reference implementation v0.1.0.)**
[![CRI test vectors](https://github.com/GHOST-UntraceableDigitalDissident/cold-root-identity/actions/workflows/tests.yml/badge.svg)](https://github.com/GHOST-UntraceableDigitalDissident/cold-root-identity/actions/workflows/tests.yml)

*A reference implementation of offline root keys, deterministic epoch keys, and lineage proofs for Nostr.*


This project provides a **minimal, reproducible standard** for managing long lived Nostr identities using **cold root keys** and **rotating epoch keys**, without any protocol changes.
All derivation, signing, and lineage verification is done through a simple Python CLI.

This is not a client or a relay.
It is a **spec plus tooling layer** meant to give developers a safe identity lifecycle model.

The v0.1.0-vectors release locks the deterministic test vector set. 
All language implementations must match these vectors exactly.

> Status: Reference implementation v0.1.0. — seeking client developer feedback.  


---

# **Why This Exists**

Nostr users normally sign every event with a single long lived private key stored on a hot device.
If that key leaks, the identity is gone forever.

Cold Root Identity solves this by separating:

* **Cold root authority key (offline forever)**
* **Deterministic epoch operational keys (hot and rotating)**

The root key is used only to sign **lineage proofs** for new epoch keys.
The root never touches a daily device, and only epoch keys are imported into Nostr clients.

A compromise no longer destroys your identity.
It only compromises a finite epoch window.

---

# Identity flow at a glance
<sub>*Cold Root Identity: root authority stays offline, clients follow deterministic rotations.*</sub>


<img src="docs/cold-root-flow.png" width="600">

For detailed specification documents, see **[`/docs`](docs/)**.

---

# **Features**

### ✔ Generate a cold root key

`init` prints a 32 byte seed you store offline.

### ✔ Deterministically derive epoch keys

`derive-epoch` outputs the epoch keypair plus a signed lineage event.

### ✔ Verify lineage proofs

`verify-lineage` ensures the root→epoch signature and tags are valid.

### ✔ No protocol changes

Lineage events use standard **NIP 01**.
Relays remain unchanged.
Clients can support this today.

---

# Reference Vectors

Cold Root Identity ships with deterministic reference vectors to guarantee consistent behavior across implementations and languages. These vectors define:  
- The canonical root seed for test purposes
- The derived root secret and public keys
- The deterministic epoch key for 2025-Q1
- The corresponding lineage event signed by the root  

These vectors are frozen under:

`tests/vectors/cold_root_identity.v1.json`

Python re-derives these values in:

`tests/test_vectors.py`

Any implementation in Go, Rust, or another language must match this file byte-for-byte for:  
- Root secret key
- Root public key
- Epoch secret key
- Epoch public key

Lineage event fields:  
- kind
- created_at
- content
- tags
- pubkey

A signed tag marks the vector freeze:  

`v0.1.0-vectors`

If a future version of the specification changes derivation semantics, a new vector file and tag will be published.

## Deterministic Timestamp Rule

Runtime lineage events use the current system time.  
Reference vectors use a deterministic timestamp derived from the epoch label:
- `YYYY-Qn` maps to the first second of that quarter in UTC
- Example: `"2025-Q1"` -> `2025-01-01T00:00:00Z` -> `1735689600`

This ensures all implementations produce identical lineage events when verifying against published vectors while keeping runtime freshness semantics intact.

## Test Suite

Run the full compliance check with:
`pytest -v`
Any change to key derivation, lineage semantics, or event structure will cause tests to fail until vectors are intentionally regenerated and versioned.

### HKDF parameters (normative)

Epoch derivation uses HKDF-SHA256 with the following exact parameters:

- IKM: the 32 byte root seed (decoded from hex)
- salt: the UTF-8 string `nostr-cold-root`
- info: the UTF-8 string `epoch:` concatenated with the epoch label  
  (example: `epoch:2025-Q1`)
- L: 32 bytes of output

Any implementation must use these parameters to reproduce the vectors in
`tests/vectors/cold_root_identity.v1.json`.

## Implementations

Cold Root Identity currently has two matching reference implementations:

- **Python**: core library under `coldroot/`  
  - Test suite: `pytest`
- **Go**: module under `go/`  
  - Test suite: `cd go && go test ./...`  
- **JavaScript (Node)**: matching implementation under `js/`, verified against the same vectors.

Both implementations reproduce the deterministic vectors in
`tests/vectors/cold_root_identity.v1.json` and are validated against the same
HKDF parameters and lineage event structure.

---
# Test Vectors Explained

Cold Root Identity ships deterministic test vectors so every implementation in every language can reproduce identical results. This prevents silent drift, keeps derivations honest, and ensures lineage validation behaves the same across clients.

## Why deterministic HKDF is required

Epoch keys must derive identically from the same `(root_seed, epoch_label)` pair across all languages.  
Using HKDF SHA256 with fixed `salt` and `info` ensures:  
- the same root seed always produces the same child seed  
- no implementation can introduce randomness or library specific behavior  
- epoch keys remain reproducible indefinitely  

If HKDF is not deterministic, lineage proofs break because clients would derive non matching keys.  

## How epoch labels bind to seeds

The epoch label is inserted directly into the HKDF `info` field:

`info = "epoch:" + <label>`

This creates:  

1. Namespace isolation  
  - Each label corresponds to a unique derivation namespace.
  - `2025-Q1` and `2025Q1` produce different keys.  

2. Re-derivability  
Anyone who knows:
- the root seed
- the epoch label
- fixed HKDF parameters

 Can re derive the same epoch key. No other metadata or state is required.

## Why the timestamp in vectors is deterministic

Runtime lineage events use actual timestamps.
Reference vectors cannot depend on clocks, so they map structured labels of the form `YYYY-Qn` to a deterministic timestamp:  

`first second of that quarter in UTC`

Example:  
`2025-Q1` -> `2025-01-01T00:00:00Z` -> `1735689600`

This ensures:  
- identical lineage events across implementations  
- stable canonical JSON  
- reproducible cross language tests  

## How lineage validation works

Each lineage event carries three critical tags:  

`["root",  <root_pubkey_hex>]`  
`["sig",   <root_signature_over_epoch_pubkey>]`  
`["epoch", <label>]`  


Clients validate lineage by:  
1. Hex decoding the epoch public key  
2. Extracting the root pubkey  
3. Extracting the signature  
4. Running:

```
ed25519_verify(
    public_key = root_pubkey,
    message    = raw_epoch_pubkey_bytes,
    signature  = sig
)
```

If valid, the client knows:  
- the epoch key was explicitly authorized by the root  
- the epoch label corresponds to the derivation namespace  
- continuity cannot be forged by clients or relays  

This is what allows safe rotation while preserving long term identity continuity.

---

# **Installation**

This tool requires Python 3.9+.

### Create an isolated environment (recommended)

Debian based systems enforce PEP 668. Use a venv:

```bash
sudo apt install python3-venv python3-pip
python3 -m venv venv
source venv/bin/activate

pip install pynacl
```

Alternatively, install PyNaCl from system packages:

```bash
sudo apt install python3-pynacl
```

Run the CLI directly:

```bash
python cold_root_identity.py --help
```

## CLI Usage

After installation, the `coldroot` command becomes available. This is the
preferred interface for exercising the CRI-01 reference implementation.

### Derive an Epoch Key

`coldroot derive --epoch 2026Q1 --root-seed <root_seed_hex>`


### Generate a Lineage Event

`coldroot lineage --epoch 2026Q1 --root-seed <root_seed_hex>`


### Verify a Lineage Event

`coldroot verify lineage.json`

The CLI performs no additional logic beyond the CRI-01 specification. All
outputs are deterministic and match the reference vectors.

---

## Commands

The CLI is the preferred interface for working with the CRI reference implementation.  
All commands are deterministic and match the reference vectors.

---

### 1. Derive a Root Seed (Cold Root)

You generate the cold root seed yourself. It is a 32 byte random value that must remain offline.

Example using Python:

```python
import os, binascii
print(binascii.hexlify(os.urandom(32)).decode())
```
Outputs:
- 32 byte root seed (hex)  
- This seed never touches a Nostr client  
- Store offline and treat as your long-term authority key  

### 2. Derive an Epoch Key

`coldroot derive --epoch 2025Q1 --root-seed <ROOT_SEED_HEX>`  

Outputs:
- epoch private key (hex)  
- epoch public key (hex)  

The epoch private key (`nsec`) is the key you import into your Nostr client for this epoch.

### 3. Generate a Lineage Event  

`coldroot lineage --epoch 2025Q1 --root-seed <ROOT_SEED_HEX>`  

Outputs a lineage event JSON containing:
- kind (default 30001)  
- pubkey (epoch pubkey)  
- created_at  
- tags:  
  - ["root", <root_pubkey_hex>]
  - ["sig", <signature_by_root_over_epoch_pubkey>]
  - ["epoch", <label>]

Clients follow this event to rotate identities safely.
Publish exactly one lineage event per epoch.

### 4. Verify a Lineage Event

`coldroot verify lineage.json`  

Validates:
- the root pubkey in the lineage event  
- the Ed25519 signature over the epoch pubkey  
- event integrity and deterministic structure  

This ensures the lineage event correctly links the epoch key to the offline root.

---

## Specification

The full Cold Root Identity specification is documented here:

**[docs/SPEC.md](./docs/SPEC.md)**

This describes:

- deterministic epoch key derivation  
- HKDF parameters  
- lineage event format (kind 30001)  
- client verification rules  
- expected client behavior  

All implementations SHOULD match the specification and reference test vectors exactly.

---

## Library API

Cold Root Identity now provides a stable Python reference implementation under the coldroot package.
It exposes three canonical functions that mirror the specification:  
The library API mirrors SPEC.md and is intended to be stable across languages.
```
from coldroot import derive_epoch_key, make_lineage_event, verify_lineage
```
### Functions
These functions define the expected behavior for implementations and correspond directly to the rules in **[docs/SPEC.md](./docs/SPEC.md)**

- derive_epoch_key(root_seed_hex, epoch_label)
Deterministically derive an ed25519 epoch keypair.

- make_lineage_event(root_sk, epoch_vk, epoch_label)
Produce a lineage event (kind 30001) signed by the offline root key.

- verify_lineage(root_pubkey_hex, event_json)
Validate lineage events according to SPEC.md.

These functions define the expected behavior for other languages and client implementations.

### Test Vectors and Compliance

Canonical test vectors for epoch derivation and lineage events are published in:

Deterministic reference vectors for both derivation and lineage validation are frozen in `tests/vectors/cold_root_identity.v1.json`. All implementations MUST match these outputs exactly.


Implementations in other languages SHOULD match these outputs exactly.
Automated tests validating determinism and lineage verification live under:
```
tests/
```

Run:
```
pytest -v
```

---

# **Derivation Scheme (Reference Standard)**

This implementation defines a deterministic, reproducible derivation process:

* **HKDF SHA256**
* Salt: `"nostr-cold-root"`
* Info: `"epoch:<label>"`
* Output: 32 byte child seed

Child seed is then transformed into an **ed25519 private key**, clamped using standard libsodium rules.

This ensures other implementations can generate identical keys from the same root.

---

# **Recommended Lineage Event Format**

`kind 30001` is the **recommended standard** for ecosystem wide interoperability.
Clients should expect lineage proofs to appear under this event kind.

Example:

```json
{
  "kind": 30001,
  "pubkey": "<epoch_pubkey_hex>",
  "created_at": 1733660000,
  "tags": [
    ["root", "<root_pubkey_hex>"],
    ["sig", "<ed25519_signature_by_root_over_raw_epoch_pubkey_bytes_hex>"],
    ["epoch", "2025Q1"]
  ],
  "content": ""
}
```

Rules:

* `pubkey` must be **raw 32 byte hex**, not npub
* the signature must be over the raw epoch pubkey bytes (no encoding, no bech32)
* only epoch keys publish lineage
* clients follow whichever epoch key has valid lineage from the root

---

# **Security Model**

## **Cold Root**

* Generated once
* Stored offline
* Never imported into a client
* Only signs epoch pubkeys

## **Epoch Keys**

* Rotating, short lived
* Imported into Nostr clients
* If compromised, only that epoch is affected
* Deterministically reproducible

## **Lineage Proofs**

* Signed by the cold root
* Verify continuity
* Allow automatic client side rotation
* Compromise becomes containable

**Important:**
If an epoch key is compromised *before* its lineage event is published, clients cannot trust or follow it.
Publish lineage immediately after moving the epoch key into a client.

---

# **Limitations**

* Reference quality, not production hardened
* No encrypted local storage (intentional for cold workflows)
* No client integrations yet


---
# Development and Tests

Cold Root Identity includes deterministic reference vectors under  
`tests/vectors/cold_root_identity.v1.json`. All implementations (Python, Go, and
JavaScript) MUST reproduce these vectors exactly.  

### Local Tests
Run the full test suite locally:

```
# Python
pytest -v

# Go
cd go
go test ./...
cd ..

# JavaScript
cd js
npm test
cd ..
```
### Continuous Integration

GitHub Actions runs Python, Go, and JavaScript vector tests on every push.
Any change that breaks determinism or lineage semantics will fail CI until
vectors are intentionally regenerated and versioned.

This guarantees cross-language correctness and enforces the CRI-01
specification at the test-vectors level.

---

# **License**

MIT.

---

# **Author**

**GHOST**
Untraceable Digital Dissident

- npub18dlusgmprudw46nracaldxe9hz4pdmrws8g6lsusy6qglcv5x48s0lh8x3  




