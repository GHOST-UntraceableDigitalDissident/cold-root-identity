# coldroot/core.py

import os
import binascii
import hashlib
import hmac
from typing import List, Tuple

from nacl import signing

# ---------- HKDF (SHA-256) ----------

def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """
    Minimal HKDF-SHA256 implementation.

    This MUST match the parameters in SPEC.md:
    - KDF: HKDF-SHA256
    - Salt: b"nostr-cold-root"
    - Info: b"epoch:" + epoch_label_utf8
    - Output length: 32 bytes
    """
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

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_polymod(values: List[int]) -> int:
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
    """
    Generate a new 32 byte root seed.
    MUST be run offline for real usage.
    """
    return os.urandom(32)


def root_seed_to_hex(seed: bytes) -> str:
    if len(seed) != 32:
        raise ValueError("root seed must be 32 bytes")
    return binascii.hexlify(seed).decode("ascii")


def signing_key_from_seed_hex(seed_hex: str) -> signing.SigningKey:
    seed = binascii.unhexlify(seed_hex)
    if len(seed) != 32:
        raise ValueError("root seed must be 32 bytes (64 hex chars)")
    return signing.SigningKey(seed)


def derive_epoch_key(root_seed_hex: str, epoch_label: str) -> Tuple[signing.SigningKey, signing.VerifyKey]:
    """
    Deterministically derive an epoch SigningKey and VerifyKey
    from a 32-byte root seed (hex) and a UTF-8 epoch label.

    This MUST match the derivation described in SPEC.md.
    """
    root_seed = binascii.unhexlify(root_seed_hex)
    if len(root_seed) != 32:
        raise ValueError("root seed must be 32 bytes (64 hex chars)")

    child_seed = hkdf_sha256(
        ikm=root_seed,
        salt=b"nostr-cold-root",
        info=b"epoch:" + epoch_label.encode("utf-8"),
        length=32,
    )
    epoch_sk = signing.SigningKey(child_seed)
    epoch_vk = epoch_sk.verify_key
    return epoch_sk, epoch_vk


def npub_from_verify_key(vk: signing.VerifyKey) -> str:
    return nostr_bech32_encode("npub", vk.encode())


def nsec_from_signing_key(sk: signing.SigningKey) -> str:
    """
    Nostr uses the 32-byte seed in nsec, not the full 64-byte key.
    """
    seed = sk._seed  # PyNaCl private attribute, stable in practice
    return nostr_bech32_encode("nsec", seed)
