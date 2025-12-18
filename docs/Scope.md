# What Cold Root Identity Does and Explicitly Does Not Solve

Cold Root Identity (CRI) is a narrow, infrastructure level identity model for Nostr. It is intentionally limited in scope. This document exists to prevent misuse, misinterpretation, and scope creep. If you are looking for a system that assigns trust, reputation, or social meaning, CRI is not it.

## What CRI Does Solve
### 1. Identity continuity over time

CRI provides a cryptographically verifiable way to answer a single question: **Which key is currently authorized to represent this identity?**

It does this by separating:  
- A long lived offline root key  
- Short lived operational epoch keys  
- Public lineage events that bind them together  

This allows identities to rotate keys without silent replacement.

### 2. Safe key rotation without protocol changes

CRI enables key rotation:
- Without changing Nostr event formats  
- Without requiring relay enforcement  
- Without invalidating historical events  

Old events remain valid under the keys that signed them.  
New events must use the newest authorized epoch key.  

Clients that understand CRI can follow identity continuity.  
Clients that do not will continue following old keys.  

This behavior is intentional.

### 3. Verifiable authorization, not trust

CRI provides cryptographic authorization:  
- Root authorizes epoch keys  
- Lineage is public and verifiable  
- Clients can independently validate correctness  

CRI makes no statements about whether an identity is good, honest, reputable, or safe. It only answers whether an identity is still the same cryptographic entity over time.

### 4. Deterministic behavior across implementations

Epoch keys are derived deterministically. Given the same root and parameters, all correct implementations derive the same keys.

This prevents:
- Silent identity forks  
- Malicious clients inventing keys  
- Implementation divergence  

Determinism keeps clients honest.

## What CRI Explicitly Does Not Solve
### 1. Trust, Reputation, or Web of Trust

CRI does not:
- Express trust  
- Assign reputation  
- Evaluate behavior  
- Decide who should be trusted  

Those are social problems. They belong to Web of Trust systems, lists, attestations, and user judgment. CRI exists below that layer.

### 2. Social recovery or key loss recovery

CRI does not provide:
- Witness based recovery  
- Social recovery  
- Quorum based restoration  
- Emergency key reset mechanisms  

If the root key is lost, identity continuity is lost. This is an explicit design choice.

### 3. Fraud detection or meatspace verification

CRI does not answer:
- Whether someone is a real person  
- Whether they are impersonating someone else  
- Whether they are abusing authority  
- Whether they are a doctor, journalist, or expert  

Cryptography cannot solve meatspace truth. CRI does not attempt to.

### 4. Historical truth or backdating prevention

CRI does not prove:
- When content was actually created  
- That historical posts are truthful  
- That an identity did not fabricate past events  

Timestamping, OTS, zaps, or external attestations may help with historical claims. They are orthogonal to CRI. CRI only governs authorization across key changes.

### 5. Backwards compatible user experience

CRI is protocol compatible, not UX preserving.

Clients that do not understand CRI will:
- Continue following old keys  
- Miss new events after rotation  
- Experience visible continuity breaks  

This is intentional. CRI refuses to silently fake continuity for unaware clients.

## Correct Layering

Think in layers:
- CRI answers: who is still the same identity over time  
- WoT answers: who should be trusted  
- Control planes answer: what to do about it  

These layers are orthogonal and composable.

CRI is not a replacement for WoT.  
WoT is not a substitute for CRI.  

They solve different problems.

## Summary

Cold Root Identity is intentionally boring infrastructure. It provides a stable identity anchor so higher level systems do not have to guess, infer, or smear trust across key changes.

If you need trust, use WoT.  
If you need recovery, use social mechanisms.  
If you need moderation, use policy systems.  
If you need to know which key is still you, use CRI.
