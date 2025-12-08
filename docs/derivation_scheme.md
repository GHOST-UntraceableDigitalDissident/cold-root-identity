# `docs/derivation_scheme.md`

```
# Deterministic Derivation Scheme (Draft)

Cold Root Identity relies on a deterministic, reproducible derivation process that produces
epoch keys from a single offline root seed. This allows any implementation (Python, Go,
Rust, hardware devices) to generate identical epoch keys given the same root seed and label.

This document defines the canonical HKDF-SHA256 scheme used for epoch derivation.

---

## 1. Root Seed Requirements

The root seed MUST be:

- exactly 32 bytes
- generated offline
- stored offline forever
- never imported into a Nostr client or used on a networked device

The seed SHOULD be generated using a CSPRNG such as `os.urandom(32)`.

Example (hex encoded):

```

4f2c35e39e9f2fa2bf5240e91c96a920bfe3a21e4135bb2bbf638777acd144ff

```

---

## 2. HKDF Parameters (Canonical)

Epoch derivation uses HKDF-SHA256 with fixed parameters to guarantee cross-language
compatibility.

- **Salt:** `"nostr-cold-root"`  (ASCII bytes)
- **Info:** `"epoch:<label>"`   (ASCII bytes)
- **Length:** `32` bytes
- **IKM (input key material):** root seed (32 raw bytes)

Where `<label>` is the epoch namespace string (e.g., `2025Q1`, `2026-01`, `v2`).

---

## 3. Derivation Process

### Step 1 — Input Key Material (IKM)

```

IKM = root_seed (32 bytes)

```

### Step 2 — HKDF Extract

```

PRK = HMAC_SHA256(salt="nostr-cold-root", IKM)

```

### Step 3 — HKDF Expand

```

OKM = HKDF-Expand(PRK, info="epoch:<label>", length=32)

```

Where the HKDF-Expand loop is:

```

T(1) = HMAC_SHA256(PRK, T(0) | info | 0x01)
T(2) = HMAC_SHA256(PRK, T(1) | info | 0x02)
...
OKM = T(1) || T(2) || ...

```

The result is truncated to 32 bytes.

### Step 4 — Interpret OKM as an ed25519 private seed

The 32-byte OKM is passed directly into the signing key constructor:

```

epoch_sk = ed25519_signing_key(OKM)
epoch_vk = epoch_sk.verify_key

```

This yields a deterministic keypair reproducible across all implementations.

---

## 4. Example (Illustrative Only)

```

root_seed = 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
label     = "2025Q1"

salt = "nostr-cold-root"
info = "epoch:2025Q1"

```

The implementation should produce (example):

```

child_seed = 5fa61c3edfcd7efb47d79b1c9b9e5ba46c514062bfd535c6cfa3ef9d8bd0f517

```

Any language producing a different value is not following the reference scheme.

---

## 5. Deterministic Guarantees

For a given `(root_seed, label)` pair:

- The derived epoch private key MUST always be identical.
- The epoch public key MUST always be identical.
- The lineage signature MUST always verify for those keys.

This ensures clients can validate identity continuity independent of implementation differences.

---

## 6. Security Notes

- HKDF-SHA256 is used specifically for forward security and namespace isolation.
- Labels MUST be chosen carefully; reusing labels produces identical keys.
- Using non-ASCII or structured labels (e.g., JSON) is discouraged.
- The root seed MUST remain offline; only derived seeds become hot keys.

---

## 7. Status

This derivation scheme is part of the **Cold Root Identity** draft specification and may
evolve as broader Nostr ecosystem feedback arrives.

