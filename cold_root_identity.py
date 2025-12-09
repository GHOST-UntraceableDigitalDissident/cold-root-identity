#!/usr/bin/env python3
"""

Cold Root Identity v0.1.1 / Epoch Key CLI

Thin wrapper around the coldroot library:
- Root seed generation
- Epoch key derivation
- Lineage event creation
- Lineage verification

Root operations MUST be run offline for real usage.
Non hardened, non production ready. Test code only.


"""

import argparse
import json
import sys
from typing import Any, Dict

from coldroot import (
    generate_root_seed,
    root_seed_to_hex,
    signing_key_from_seed_hex,
    derive_epoch_key,
    npub_from_verify_key,
    nsec_from_signing_key,
    make_lineage_event,
    verify_lineage,
)


def cmd_init(args: argparse.Namespace) -> None:
    seed = generate_root_seed()
    seed_hex = root_seed_to_hex(seed)

    root_sk = signing_key_from_seed_hex(seed_hex)
    root_vk = root_sk.verify_key

    print("=== Cold Root Seed (STORE OFFLINE, NEVER ONLINE) ===")
    print(seed_hex)
    print()
    print("Root public key (for reference only, can be shared):")
    print(root_vk.encode().hex())
    print()
    print("Root npub (optional, do not use for posting):")
    print(npub_from_verify_key(root_vk))
    print()
    print("Write the seed hex down on paper and delete this file/output if saved.")


def cmd_derive_epoch(args: argparse.Namespace) -> None:
    root_seed_hex = args.root_seed_hex.lower()
    label = args.label
    kind = args.kind

    # Root key and epoch key
    root_sk = signing_key_from_seed_hex(root_seed_hex)
    root_vk = root_sk.verify_key

    epoch_sk, epoch_vk = derive_epoch_key(root_seed_hex, label)

    # Build lineage event via library
    event: Dict[str, Any] = make_lineage_event(
        root_sk=root_sk,
        epoch_vk=epoch_vk,
        epoch_label=label,
        kind=kind,
    )

    print("=== Derived Epoch Key ===")
    print(f"Label: {label}")
    print(f"Epoch pubkey (hex): {epoch_vk.encode().hex()}")
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

    # If root pubkey is provided, use it. Otherwise, take it from the event.
    explicit_root = args.root_pubkey_hex

    root_from_event = None
    for tag in event.get("tags", []):
        if isinstance(tag, list) and len(tag) >= 2 and tag[0] == "root":
            root_from_event = tag[1]
            break

    root_to_use = explicit_root or root_from_event

    if not root_to_use:
        print("Could not determine root pubkey (no --root-pubkey-hex and no root tag).", file=sys.stderr)
        sys.exit(1)

    if verify_lineage(root_to_use, event):
        print("VALID lineage event.")
        print(f"Root pubkey:  {root_to_use}")
        print(f"Epoch pubkey: {event.get('pubkey')}")
    else:
        print("INVALID lineage event.", file=sys.stderr)
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cold Root Identity / Epoch Key CLI"
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
    p_ver.add_argument(
        "--root-pubkey-hex",
        help="optional explicit root pubkey hex; if omitted, root tag from event is used",
    )
    p_ver.set_defaults(func=cmd_verify_lineage)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
