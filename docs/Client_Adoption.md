# Client Adoption Guide

This section describes the minimum rules a Nostr client must follow to support Cold Root Identity.  
No protocol changes are required.

## Overview

Cold Root Identity separates long-lived identity authority (root key) from short lived operational keys (epoch keys).

Clients do **not** generate or manage root keys.
Clients only follow published lineage events and use the most recent valid epoch key for signing and verification.

## Discovering Lineage Events

- Lineage events are published as regular Nostr events (recommended kind `30001`)  
- Clients discover them the same way they discover any other event:  
  - by subscribing to relays  
  - by fetching user history  
- No special relay support is required  

## Validating a Lineage Event
A lineage event is valid if all of the following are true:  
1. The event contains:  
- an epoch public key (`pubkey`)  
- a `root` tag containing the root public key  
- a `sig` tag containing a signature  
- an `epoch` label  

2. The signature is a valid Ed25519 signature by the root key over the raw epoch public key bytes  
3. The event structure matches the CRI specification

Clients MUST NOT synthesize lineage events.  
Clients may only follow lineage events that exist on relays.  

## Freshness Rule

If multiple valid lineage events exist for the same root:  
- Clients MUST select the event with the highest `created_at` timestamp  
- Older lineage events remain valid for historical verification  
- Only the freshest valid event determines the **active epoch key**

This rule prevents ambiguity and resolves conflicts deterministically.

## Key Usage Rules

- Events created before a rotation remain associated with their original epoch key  
- Events created after a rotation MUST use the new epoch key  
- Clients SHOULD display identity continuity across epoch boundaries  

Clients are not required to re-sign or migrate old events.

## Missing or Invalid Lineage

If no valid lineage event is found:  
- Clients MAY treat the user as a legacy single-key identity  
- Clients MAY show a warning or degraded trust indicator  
- Posting MAY continue using the last known key  

If a lineage event is invalid:  
- It MUST be ignored  
- It MUST NOT replace an existing valid lineage

## Ignoring Lineage

Clients MAY ignore CRI entirely.

Ignoring lineage does not break Nostr compatibility.  
It only results in identity discontinuity when key rotation occurs.  

## Client Responsibilities (Summary)

Clients are responsible for:  
- discovering lineage events
- validating lineage signatures  
- selecting the freshest valid lineage  
- switching active signing keys when rotation occurs  

Clients are NOT responsible for:  
- generating root keys  
- generating epoch keys  
- enforcing rotation schedules  
- storing secrets long term

--- 

This guide is intentionally minimal.  
If a client follows these rules, it is Cold Root Identity compatible.  

For a concrete implementation flow, see `CLIENT_PSEUDOCODE.md`.

--- 
