#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from .core import derive_epoch_key, signing_key_from_seed_hex, root_seed_to_hex
from .lineage import make_lineage_event, verify_lineage


def cmd_derive(args):
    """
    coldroot derive --epoch 2026Q1 --root-seed <hex>
    """
    label = args.epoch
    root_seed_hex = args.root_seed

    sk, vk = derive_epoch_key(root_seed_hex=root_seed_hex, epoch_label=label)

    out = {
        "epoch": label,
        "sk_hex": sk._seed.hex(),
        "pk_hex": vk.encode().hex(),
    }
    print(json.dumps(out, indent=2))


def cmd_lineage(args):
    """
    coldroot lineage --epoch 2026Q1 --root-seed <hex>
    """
    label = args.epoch
    root_seed_hex = args.root_seed

    # derive epoch key so we can access pk
    sk, vk = derive_epoch_key(root_seed_hex=root_seed_hex, epoch_label=label)
    epoch_pk = vk

    # load root secret key from seed
    root_seed_bytes = bytes.fromhex(root_seed_hex)
    root_sk = signing_key_from_seed_hex(root_seed_hex)

    event = make_lineage_event(
        root_sk=root_sk,
        epoch_vk=epoch_pk,
        epoch_label=label,
    )

    print(json.dumps(event, indent=2))


def cmd_verify(args):
    """
    coldroot verify lineage.json
    """
    path = Path(args.file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with path.open() as f:
        event = json.load(f)

    root_hex, _, _ = extract_root_tag(event)
    if root_hex is None:
        print("error: lineage event missing root tag", file=sys.stderr)
        sys.exit(1)

    ok = verify_lineage(root_pubkey_hex=root_hex, event=event)
    if ok:
        print("valid")
    else:
        print("invalid")
        sys.exit(1)


def extract_root_tag(event):
    """
    Small helper so the CLI can identify the root pubkey hex from the lineage event.
    """
    for tag in event.get("tags", []):
        if tag[0] == "root":
            return tag[1], None, None
    return None, None, None


def build_parser():
    p = argparse.ArgumentParser(prog="coldroot", description="Cold Root Identity CLI")
    sub = p.add_subparsers(dest="cmd")

    # derive
    d = sub.add_parser("derive", help="derive epoch key")
    d.add_argument("--epoch", required=True, help="epoch label, e.g. 2026Q1")
    d.add_argument("--root-seed", required=True, help="32-byte root seed in hex")
    d.set_defaults(func=cmd_derive)

    # lineage
    l = sub.add_parser("lineage", help="create lineage event")
    l.add_argument("--epoch", required=True, help="epoch label, e.g. 2026Q1")
    l.add_argument("--root-seed", required=True, help="32-byte root seed in hex")
    l.set_defaults(func=cmd_lineage)

    # verify
    v = sub.add_parser("verify", help="verify lineage JSON file")
    v.add_argument("file", help="path to lineage.json")
    v.set_defaults(func=cmd_verify)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
