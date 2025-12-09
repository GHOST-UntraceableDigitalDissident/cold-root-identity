# coldroot/lineage.py

import binascii
import time
from typing import Dict, Optional, Tuple

from nacl import signing
from nacl.exceptions import BadSignatureError

from .core import npub_from_verify_key  # optional, if you want helpers here too


def make_lineage_event(
    root_sk: signing.SigningKey,
    epoch_vk: signing.VerifyKey,
    epoch_label: str,
    kind: int = 30001,
    created_at: Optional[int] = None,
) -> Dict:
    """
    Build a lineage event dict as defined in SPEC.md.

    - kind: recommended 30001
    - pubkey: hex encoded epoch pubkey (32 bytes)
    - tags:
        ["root",  "<root_pubkey_hex>"]
        ["sig",   "<hex_signature_by_root_over_epoch_pubkey_bytes>"]
        ["epoch", "<epoch_label>"]
    - content: ""
    """
    if created_at is None:
        created_at = int(time.time())

    root_vk = root_sk.verify_key
    epoch_pub_bytes = epoch_vk.encode()

    # Sign raw epoch pubkey bytes with root key
    sig = root_sk.sign(epoch_pub_bytes).signature

    event = {
        "kind": kind,
        "pubkey": epoch_pub_bytes.hex(),
        "created_at": created_at,
        "tags": [
            ["root", root_vk.encode().hex()],
            ["sig", sig.hex()],
            ["epoch", epoch_label],
        ],
        "content": "",
    }
    return event


def _extract_lineage_tags(event: Dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Internal helper to pull out (root_hex, sig_hex, epoch_label) from tags.
    """
    tags = event.get("tags", [])
    root_hex = None
    sig_hex = None
    epoch_label = None

    for tag in tags:
        if not isinstance(tag, list) or len(tag) < 2:
            continue
        if tag[0] == "root":
            root_hex = tag[1]
        elif tag[0] == "sig":
            sig_hex = tag[1]
        elif tag[0] == "epoch":
            epoch_label = tag[1]

    return root_hex, sig_hex, epoch_label


def verify_lineage(root_pubkey_hex: str, event: Dict) -> bool:
    """
    Verify a lineage event according to SPEC.md.

    Steps:
    - kind must be 30001
    - root tag must be present and match root_pubkey_hex
    - signature must be a valid ed25519 signature by root over raw epoch pubkey bytes

    Returns:
        True if valid, False otherwise.
    """
    if event.get("kind") != 30001:
        return False

    pubkey_hex = event.get("pubkey")
    if not isinstance(pubkey_hex, str):
        return False

    root_hex, sig_hex, _ = _extract_lineage_tags(event)
    if not (root_hex and sig_hex and pubkey_hex):
        return False

    # root in event must match expected root
    if root_hex.lower() != root_pubkey_hex.lower():
        return False

    try:
        root_pub = binascii.unhexlify(root_hex)
        epoch_pub = binascii.unhexlify(pubkey_hex)
        sig = binascii.unhexlify(sig_hex)
    except (binascii.Error, ValueError):
        return False

    try:
        vk = signing.VerifyKey(root_pub)
        vk.verify(epoch_pub, sig)
    except BadSignatureError:
        return False

    return True
