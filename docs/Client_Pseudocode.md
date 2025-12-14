# Sample Client Pseudocode Flow (CRI-01)

This document provides a reference client flow for implementing Cold Root Identity.  
It is informational and non normative.

## Goal:
- Discover lineage events
- Validate them
- Select freshest valid epoch key
- Use that key for signing new events
- Preserve old keys for history

This flow assumes no protocol changes and operates entirely within existing Nostr event semantics.

------------------------------------------------------------
## Data structures

Note: In CRI, the root public key is the stable identity anchor. Epoch public keys are operational and rotate.

```
state:
  root_pubkey_hex_by_user_pubkey: map[user_pubkey_hex] -> root_pubkey_hex  
  active_epoch_pubkey_hex_by_user: map[user_pubkey_hex] -> epoch_pubkey_hex  
  active_epoch_created_at_by_user: map[user_pubkey_hex] -> int  
  cached_lineage_event_id_by_user: map[user_pubkey_hex] -> event_id
```

------------------------------------------------------------
## Helpers
```
function parse_lineage_tags(event):  
  root_hex = null  
  sig_hex  = null  
  epoch_label = null  

  for tag in event.tags:  
    if tag[0] == "root":  root_hex = tag[1]  
    if tag[0] == "sig":   sig_hex  = tag[1]  
    if tag[0] == "epoch": epoch_label = tag[1]  

  return (root_hex, sig_hex, epoch_label)  

function is_valid_lineage_event(event):  
  if event.kind != 30001: return false  
  if event.pubkey is missing: return false  
  if event.created_at is missing: return false  

  (root_hex, sig_hex, epoch_label) = parse_lineage_tags(event)  
  if root_hex is null or sig_hex is null or epoch_label is null: return false  

  epoch_pub_bytes = hex_to_bytes(event.pubkey)     # raw 32 bytes  
  root_pub_bytes  = hex_to_bytes(root_hex)         # raw 32 bytes  
  sig_bytes       = hex_to_bytes(sig_hex)          # raw 64 bytes  
```
## CRI-01 signature rule:
  
  root signs the raw epoch pubkey bytes (not the event hash)
  ```
  if ed25519_verify(pubkey=root_pub_bytes,
                    message=epoch_pub_bytes,
                    signature=sig_bytes) == false:
    return false

  return true
```
## Freshness Rule

Among valid lineage events for the same root identity:  
- Select the event with the highest `created_at`  
- If `created_at` ties, use deterministic tie breaking (e.g. lexicographic event id)  

```
function choose_fresher(a_event, b_event):
  # return the fresher valid lineage event using created_at
  if a_event.created_at > b_event.created_at: return a_event
  if a_event.created_at < b_event.created_at: return b_event

  # tie breaker (recommended): deterministic ordering
  # pick lexicographically highest event id if both have same timestamp
  if a_event.id > b_event.id: return a_event
  else: return b_event
```
------------------------------------------------------------
## Discovery / ingestion path
```
function on_receive_event(event):
  # called for every event from relay subscriptions

  if event.kind != 30001:
    return

  if is_valid_lineage_event(event) == false:
    return

  user_pubkey_hex = event.pubkey   # in CRI lineage, event.pubkey is epoch pubkey
  # But we still need "which user identity this belongs to?"
  # CRI-01 convention: lineage events are authored by the CURRENT epoch key.
  # Therefore: the author pubkey *is* the epoch pubkey.
  # The stable user identity is learned from the root tag.
  (root_hex, _, _) = parse_lineage_tags(event)

  # If this is the first time we see this root for this user identity:
  # treat root_hex as the stable identity anchor.
  # Some clients will store mapping root->active epoch; others store "user identity = root".
  stable_identity = root_hex

  # Retrieve current best lineage for this stable identity
  current_created_at = active_epoch_created_at_by_user.get(stable_identity)
  current_epoch_pub  = active_epoch_pubkey_hex_by_user.get(stable_identity)
  current_event_id   = cached_lineage_event_id_by_user.get(stable_identity)

  if current_created_at is null:
    # First valid lineage we have seen: adopt it
    active_epoch_created_at_by_user[stable_identity] = event.created_at
    active_epoch_pubkey_hex_by_user[stable_identity] = event.pubkey
    cached_lineage_event_id_by_user[stable_identity] = event.id
    return
```
  # Freshness rule:
  highest `created_at` wins among valid lineage events
  ```
  if event.created_at > current_created_at:
    active_epoch_created_at_by_user[stable_identity] = event.created_at
    active_epoch_pubkey_hex_by_user[stable_identity] = event.pubkey
    cached_lineage_event_id_by_user[stable_identity] = event.id
    return

  if event.created_at == current_created_at:
    # Optional tie-breaker to handle duplicate timestamps deterministically
    if event.id > current_event_id:
      active_epoch_created_at_by_user[stable_identity] = event.created_at
      active_epoch_pubkey_hex_by_user[stable_identity] = event.pubkey
      cached_lineage_event_id_by_user[stable_identity] = event.id
    return

  # Older lineage events are ignored for "active key" selection
  return
```
------------------------------------------------------------
## Signing new events
```
function get_active_signing_key_for_user(stable_identity):
  # stable_identity is the root pubkey hex used as the long-lived account identifier
  epoch_pub = active_epoch_pubkey_hex_by_user.get(stable_identity)

  if epoch_pub is null:
    # No lineage found: legacy behavior
    # Use existing single-key identity behavior for this account
    return legacy_signing_key_for_account(stable_identity)

  # In CRI usage, the client must have the epoch private key imported for this epoch
  # (stored in secure key store / OS keystore)
  return secure_keystore_lookup_epoch_private_key(epoch_pub)

function sign_new_event(stable_identity, event_template):
  sk = get_active_signing_key_for_user(stable_identity)
  return nostr_sign(event_template, sk)
```
------------------------------------------------------------
## Fetching user history (verification / display)
```
function verify_event_author_identity(event, stable_identity):
  # For display and verification, the pubkey on a normal nostr event is the epoch pubkey.
  # The client may choose to show continuity by mapping epoch pubkeys back to the same root identity.

  epoch_pub = event.pubkey
  active_epoch_pub = active_epoch_pubkey_hex_by_user.get(stable_identity)

  if active_epoch_pub is null:
    # No CRI lineage: legacy validation
    return legacy_verify(event)

  # Verify normal Nostr signature using epoch_pub (standard Nostr rule)
  if nostr_verify(event, epoch_pub) == false:
    return false

  # Optional: if you have cached older valid lineage events, you can confirm
  # that epoch_pub belongs to stable_identity’s root by checking a lineage event
  # that links root -> epoch_pub.
  return true
```
------------------------------------------------------------
## Client behavior guidance

- Clients MUST NOT synthesize lineage events.  
- Clients MUST follow the freshest valid lineage event (highest `created_at`).  
- Clients MAY ignore CRI entirely (results in discontinuity on rotations). 
- Clients SHOULD cache the root identity mapping so the UI remains continuous.

This document is a reference flow only. Clients may vary in internal architecture as long as the observable behavior matches CRI-01.

--- 

