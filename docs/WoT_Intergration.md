# How WoT Systems Can Reference Cold Root Identity (Non-Normative)

This document describes one possible way Web of Trust (WoT) systems may reference Cold Root Identity (CRI).

It is non normative. It does not define WoT behavior, trust semantics, or policy decisions. Its purpose is to show how CRI can be composed with WoT systems without entangling responsibilities.

## Design intent

CRI and WoT solve different problems.
- CRI provides cryptographic identity continuity over time.  
- WoT systems evaluate trust, reputation, and behavior.  

This document exists to keep those layers separate while allowing them to interoperate.

## Identity anchor

In CRI, the root public key acts as the long lived identity anchor. It represents continuity across all epoch keys derived from it. WoT systems may treat the root public key, or a stable hash of it, as the canonical identifier for an identity over time.
This allows trust signals to remain stable even as operational keys rotate.

## Current representative key

At any given time, an identity is represented by a current epoch key.

The validity of that epoch key is established by:
- A publicly visible lineage event  
- Signed by the root key  
- Authorizing that epoch key  

WoT systems may resolve:

root key  
-> highest valid lineage event  
-> currently authorized epoch key  

This resolution step answers **which key is currently allowed to speak for this identity.**

## Referencing identity in WoT statements

WoT systems may reference identities in one of two ways:

### 1. Root anchored reference  
- Trust statements reference the root public key.  
- Clients resolve the current epoch key via CRI lineage when verifying events.

### 2.Epoch plus lineage reference  
Trust statements reference:
- an epoch public key  
- plus a valid lineage proof back to the root  

Clients verify continuity before applying trust.

Both approaches preserve identity continuity without binding trust to a single static key.

## Trust logic is out of scope

CRI does not define:
- How trust is assigned  
- How reputation is calculated  
- How behavior is evaluated  
- How fraud is detected  
- How moderation or policy decisions are made  

All trust semantics remain entirely within the WoT system. CRI only supplies a stable identity anchor and a verifiable authorization chain.

## Failure behavior

If lineage cannot be verified:
- Identity continuity cannot be established  
- Trust SHOULD NOT be silently transferred  
- WoT systems may treat the identity as new or unknown
  
Explicit failure is preferred over inferred continuity.

## Relationship to social recovery

Social recovery mechanisms may coexist with CRI but are conceptually separate.
- CRI addresses cryptographic authorization  
- Social recovery addresses trust restoration  

This document does not define recovery workflows.

## Summary

Cold Root Identity provides a stable, cryptographic notion of **who is still who over time**. Web of Trust systems provide social and behavioral judgment.
By anchoring trust to the CRI root key and resolving current representatives through lineage, WoT systems can avoid trust smearing across key rotations without inheriting identity lifecycle complexity.
