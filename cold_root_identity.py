#!/usr/bin/env python3
"""
Cold Root Identity / Epoch Key CLI Prototype

Reference implementation of:
- Cold root seed generation
- Deterministic epoch key derivation (HKDF-SHA256)
- Lineage event signing (kind 30001 by default)
- Lineage verification

This is a research / prototype tool.
Run root operations offline. Not production hardened.
"""

import argparse
import binascii
import json
import os
import sys
import time
from typing import List

from nacl import signing
from nacl.exceptions import BadSignatureError

import hashlib
import hmac


# ---------- HKDF (SHA-256) ----------

def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """Minimal HKDF-SHA256 implementation."""
    if not salt:
        salt = b"\x00" * hashlib.sha256().digest_size

    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t = b""
    okm = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


# ---------- Bech32 (for npub / nsec) ----------

# Simple Bech32 implementation (BIP-0173 style)

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values: List[int]) -> int:
    """Internal function that computes the Bech32 checksum."""
    generator = [0x3b6a57b2, 0x26508e6d,
                 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = (chk >> 25) & 0xFF
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            if ((b >> i) & 1) != 0:
                chk ^= generator[i]
    return chk


def bech32_hrp_expand(hrp: str) -> List[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_create_checksum(hrp: str, data: List[int]) -> List[int]:
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def bech32_encode(hrp: str, data: List[int]) -> str:
    combined = data + bech32_create_checksum(hrp, data)
    return hrp + "1" + "".join([CHARSET[d] for d in combined])


def convert_bits(data: bytes, from_bits: int, to_bits: int, pad: bool = True) -> List[int]:
    """General power-of-2 base conversion. Used for 8->5 bit conversion."""
    acc = 0
    bits = 0
    ret: List[int] = []
    maxv = (1 << to_bits) - 1
    max_acc = (1 << (from_bits + to_bits - 1)) - 1

    for b in data:
        if b < 0 or (b >> from_bits):
            return []
        acc = ((acc << from_bits) | b) & max_acc
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (to_bits - bits)) & maxv)
    elif bits >= from_bits or ((acc << (to_bits - bits)) & maxv):
        return []
    return ret


def nostr_bech32_encode(hrp: str, data: bytes) -> str:
    five_bit = convert_bits(data, 8, 5, True)
    if not five_bit:
        raise ValueError("failed to convert bits for bech32")
    return bech32_encode(hrp, five_bit)


# ---------- Key helpers ----------

def generate_root_seed() -> bytes:
    return os.urandom(32)


def signing_key_from_seed(seed_hex: str) -> signing.SigningKey:
    seed = binascii.unhexlify(seed_hex)
    if len(seed) != 32:
        raise ValueError("root seed must be 32 bytes (64 hex chars)")
    return signing.SigningKey(seed)


def derive_epoch_signing_key(root_seed_hex: str, label: str) -> signing.SigningKey:
    root_seed = binascii.unhexlify(root_seed_hex)
    if len(root_seed) != 32:
        raise ValueError("root seed must be 32 bytes (64 hex chars)")
    child_seed = hkdf_sha256(
        ikm=root_seed,
        salt=b"nostr-cold-root",
        info=b"epoch:" + label.encode("utf-8"),
        length=32,
    )
    return signing.SigningKey(child_seed)


def npub_from_verify_key(vk: signing.VerifyKey) -> str:
    return nostr_bech32_encode("npub", vk.encode())


def nsec_from_signing_key(sk: signing.SigningKey) -> str:
    # Nostr uses the 32-byte seed in nsec, not the full 64-byte key
    seed = sk._seed  # private attribute but stable in PyNaCl
    return nostr_bech32_encode("nsec", seed)


# ---------- CLI commands ----------

def cmd_init(args: argparse.Namespace) -> None:
    seed = generate_root_seed()
    seed_hex = binascii.hexlify(seed).decode("ascii")

    sk = signing.SigningKey(seed)
    vk = sk.verify_key

    print("=== Cold Root Seed (STORE OFFLINE, NEVER ONLINE) ===")
    print(seed_hex)
    print()
    print("Root public key (for reference only, can be shared):")
    print(vk.encode().hex())
    print()
    print("Root npub (optional, do not use for posting):")
    print(npub_from_verify_key(vk))
    print()
    print("Write the seed hex down on paper and delete this file/output if saved.")


def cmd_derive_epoch(args: argparse.Namespace) -> None:
    root_seed_hex = args.root_seed_hex.lower()
    label = args.label

    # create signing keys
    root_sk = signing_key_from_seed(root_seed_hex)
    root_vk = root_sk.verify_key

    epoch_sk = derive_epoch_signing_key(root_seed_hex, label)
    epoch_vk = epoch_sk.verify_key

    # sign epoch pubkey with root key
    epoch_pub_bytes = epoch_vk.encode()
    sig = root_sk.sign(epoch_pub_bytes).signature

    # lineage event
    created_at = int(time.time())
    kind = args.kind

    event = {
        "kind": kind,
        "pubkey": epoch_pub_bytes.hex(),
        "created_at": created_at,
        "tags": [
            ["root", root_vk.encode().hex()],
            ["sig", sig.hex()],
            ["epoch", label],
        ],
        "content": "",
    }

    print("=== Derived Epoch Key ===")
    print(f"Label: {label}")
    print(f"Epoch pubkey (hex): {epoch_pub_bytes.hex()}")
    print(f"Epoch npub: {npub_from_verify_key(epoch_vk)}")
    print()
    print("Epoch nsec (IMPORT THIS INTO YOUR CLIENT):")
    print(nsec_from_signing_key(epoch_sk))
    print()
    print("=== Lineage Event JSON (publish from the epoch key) ===")
    print(json.dumps(event, indent=2))


def cmd_verify_lineage(args: argparse.Namespace) -> None:
    with open(args.event_file, "r", encoding="utf-8") as f:
        event = json.load(f)

    # Extract fields
    pubkey_hex = event.get("pubkey")
    tags = event.get("tags", [])

    root_hex = None
    sig_hex = None
    label = None

    for tag in tags:
        if not isinstance(tag, list) or len(tag) < 2:
            continue
        if tag[0] == "root":
            root_hex = tag[1]
        elif tag[0] == "sig":
            sig_hex = tag[1]
        elif tag[0] == "epoch":
            label = tag[1]

    if not (pubkey_hex and root_hex and sig_hex):
        print("Missing root/sig/pubkey tags in lineage event.", file=sys.stderr)
        sys.exit(1)

    root_pub = binascii.unhexlify(root_hex)
    epoch_pub = binascii.unhexlify(pubkey_hex)
    sig = binascii.unhexlify(sig_hex)

    try:
        vk = signing.VerifyKey(root_pub)
        vk.verify(epoch_pub, sig)
    except BadSignatureError:
        print("INVALID: signature does not verify for given root and epoch.", file=sys.stderr)
        sys.exit(1)

    print("VALID lineage event.")
    print(f"Root pubkey:  {root_hex}")
    print(f"Epoch pubkey: {pubkey_hex}")
    if label:
        print(f"Epoch label:  {label}")


# ---------- Main ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cold Root Identity / Epoch Key CLI prototype"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="generate a new cold root seed")
    p_init.set_defaults(func=cmd_init)

    # derive-epoch
    p_der = sub.add_parser(
        "derive-epoch",
        help="derive an epoch key + lineage event from a cold root seed",
    )
    p_der.add_argument(
        "--root-seed-hex",
        required=True,
        help="32-byte root seed in hex (64 chars). RUN OFFLINE.",
    )
    p_der.add_argument(
        "--label",
        required=True,
        help="epoch label, e.g. 2025Q1 or 2026-01",
    )
    p_der.add_argument(
        "--kind",
        type=int,
        default=30001,
        help="event kind to use for lineage (default: 30001)",
    )
    p_der.set_defaults(func=cmd_derive_epoch)

    # verify-lineage
    p_ver = sub.add_parser(
        "verify-lineage",
        help="verify a lineage event JSON file",
    )
    p_ver.add_argument(
        "event_file",
        help="path to lineage event JSON",
    )
    p_ver.set_defaults(func=cmd_verify_lineage)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

