"""
Stable reference API for Cold Root Identity test vectors.

This wraps the internal core + lineage implementation into a minimal,
stable surface that the vector generator and tests can depend on.
"""

from typing import Any, Dict

from nacl import signing

from coldroot.core import derive_epoch_key as _derive_epoch_key_impl
from coldroot.lineage import make_lineage_event as _make_lineage_event_impl

import datetime as _dt

def _deterministic_created_at(label: str) -> int:
    """
    Convert an epoch label like '2025-Q1' into a deterministic timestamp.

    For reproducible test vectors across Python, Go, Rust, etc.
    """
    try:
        year_str, quarter_str = label.split("-Q")
        year = int(year_str)
        quarter = int(quarter_str)
    except Exception:
        raise ValueError(f"Invalid epoch label format: {label!r}")

    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Invalid quarter in label: {label!r}")

    # First month of the quarter: 1, 4, 7, 10
    month = (quarter - 1) * 3 + 1

    dt = _dt.datetime(year, month, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    return int(dt.timestamp())


def seed_to_root_key(seed: bytes) -> bytes:
    """
    For the spec, the 32-byte seed *is* the root secret key material.
    We just validate length and return it.
    """
    if len(seed) != 32:
        raise ValueError(f"Expected 32-byte seed, got {len(seed)} bytes")
    return seed


def sk_to_pk(sk: bytes) -> bytes:
    """
    Convert secret key bytes to public key bytes using PyNaCl.
    """
    sk_obj = signing.SigningKey(sk)
    vk_obj = sk_obj.verify_key
    return vk_obj.encode()  # 32-byte pubkey


def encode_nsec(sk: bytes) -> str:
    """
    Placeholder for future bech32 nsec encoding.
    For v1 vectors we leave this unimplemented and keep JSON fields null.
    """
    raise NotImplementedError("nsec encoding not wired yet for reference vectors")


def encode_npub(pk: bytes) -> str:
    """
    Placeholder for future bech32 npub encoding.
    For v1 vectors we leave this unimplemented and keep JSON fields null.
    """
    raise NotImplementedError("npub encoding not wired yet for reference vectors")


def derive_epoch_key(root_sk: bytes, label: str) -> bytes:
    """
    Derive epoch secret key bytes from root secret key bytes + label.

    Internally, coldroot.core.derive_epoch_key expects a hex seed string and
    returns (SigningKey, VerifyKey). We adapt that to return raw sk bytes.
    """
    root_seed_hex = root_sk.hex()
    epoch_sk_obj, epoch_vk_obj = _derive_epoch_key_impl(root_seed_hex, label)
    return epoch_sk_obj.encode()  # 32-byte epoch secret key

def build_lineage_event(root_sk: bytes, epoch_pk: bytes, label: str) -> Dict[str, Any]:
    root_sk_obj = signing.SigningKey(root_sk)
    epoch_vk_obj = signing.VerifyKey(epoch_pk)

    created_at = _deterministic_created_at(label)

    return _make_lineage_event_impl(
        root_sk=root_sk_obj,
        epoch_vk=epoch_vk_obj,
        epoch_label=label,
        created_at=created_at,
    )




    # We expect make_lineage_event to already produce the full event dict:
    # {
    #   "kind": int,
    #   "created_at": int,
    #   "content": str,
    #   "tags": list,
    #   "pubkey": "<hex>",
    #   "id": "<hex>",
    #   "sig": "<hex>",
    # }
    return event
