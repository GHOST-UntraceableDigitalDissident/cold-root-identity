#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict
import sys

# Add repo root so Python can import coldroot.*
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Project imports: use the stable reference API
from coldroot.reference_api import (
    seed_to_root_key,
    sk_to_pk,
    encode_nsec,
    encode_npub,
    derive_epoch_key,
    build_lineage_event,
)

VECTORS_PATH = ROOT / "tests" / "vectors" / "cold_root_identity.v1.json"



def load_vectors() -> Dict[str, Any]:
    with VECTORS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_vectors(data: Dict[str, Any]) -> None:
    # Pretty-print and keep key order stable
    with VECTORS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")


def populate_root(data: Dict[str, Any]) -> None:
    root = data["root"]

    seed_hex = root["seed_hex"]
    seed = bytes.fromhex(seed_hex)

    # For now, the seed is the root secret key
    root_sk = seed_to_root_key(seed)
    root_pk = sk_to_pk(root_sk)

    root["sk_hex"] = root_sk.hex()
    root["pk_hex"] = root_pk.hex()

    # Leave nsec/npub as null for v1 vectors
    # root["nsec"] = encode_nsec(root_sk)
    # root["npub"] = encode_npub(root_pk)

def populate_epochs(data: Dict[str, Any]) -> None:
    root = data["root"]
    root_sk = bytes.fromhex(root["sk_hex"])

    for epoch in data.get("epochs", []):
        label = epoch["label"]

        # Derive epoch key from root + label
        epoch_sk = derive_epoch_key(root_sk, label)
        epoch_pk = sk_to_pk(epoch_sk)

        epoch["sk_hex"] = epoch_sk.hex()
        epoch["pk_hex"] = epoch_pk.hex()

        # Leave npub null for now
        # epoch["npub"] = encode_npub(epoch_pk)

           # Build lineage event
        lineage = build_lineage_event(root_sk=root_sk, epoch_pk=epoch_pk, label=label)

        # For v1 we only require the core fields your implementation defines
        required_fields = ["kind", "created_at", "content", "tags", "pubkey"]
        for field in required_fields:
            if field not in lineage:
                raise ValueError(f"lineage event missing field '{field}' for epoch '{label}'")

        # id/sig (event-level) are optional for now
        epoch["lineage_event"] = {
            "kind": lineage["kind"],
            "created_at": lineage["created_at"],
            "content": lineage["content"],
            "tags": lineage["tags"],
            "pubkey": lineage["pubkey"],
            "id": lineage.get("id"),
            "sig": lineage.get("sig"),
        }




def main() -> None:
    if not VECTORS_PATH.exists():
        raise SystemExit(f"Vector file not found: {VECTORS_PATH}")

    data = load_vectors()

    populate_root(data)
    populate_epochs(data)

    save_vectors(data)
    print(f"Updated vectors written to {VECTORS_PATH}")


if __name__ == "__main__":
    main()
