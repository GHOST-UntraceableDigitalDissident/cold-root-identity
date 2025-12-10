import json
from pathlib import Path
import sys

# Add repo root so we can import coldroot.*
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from coldroot.reference_api import (
    seed_to_root_key,
    sk_to_pk,
    derive_epoch_key,
    build_lineage_event,
)

VECTORS_PATH = ROOT / "tests" / "vectors" / "cold_root_identity.v1.json"


def load_vectors():
    with VECTORS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_root_vector():
    data = load_vectors()
    root = data["root"]

    # Re-derive root from seed
    seed_hex = root["seed_hex"]
    seed = bytes.fromhex(seed_hex)

    root_sk = seed_to_root_key(seed)
    root_pk = sk_to_pk(root_sk)

    # Compare against frozen vectors
    assert root["sk_hex"] == root_sk.hex()
    assert root["pk_hex"] == root_pk.hex()


def test_epoch_2025_q1_vector():
    data = load_vectors()
    root = data["root"]
    epochs = data["epochs"]

    epoch = next(e for e in epochs if e["id"] == "epoch-2025-Q1")

    root_sk = bytes.fromhex(root["sk_hex"])

    # Re-derive epoch key
    label = epoch["label"]
    epoch_sk = derive_epoch_key(root_sk, label)
    epoch_pk = sk_to_pk(epoch_sk)

    # Compare against frozen vectors
    assert epoch["sk_hex"] == epoch_sk.hex()
    assert epoch["pk_hex"] == epoch_pk.hex()


def test_epoch_2025_q1_lineage_event():
    data = load_vectors()
    root = data["root"]
    epochs = data["epochs"]

    epoch = next(e for e in epochs if e["id"] == "epoch-2025-Q1")
    label = epoch["label"]

    root_sk = bytes.fromhex(root["sk_hex"])
    epoch_pk = bytes.fromhex(epoch["pk_hex"])

    expected = epoch["lineage_event"]

    # Rebuild lineage event
    actual = build_lineage_event(root_sk=root_sk, epoch_pk=epoch_pk, label=label)

    # For v1 we enforce core fields that matter to the spec
    for field in ["kind", "created_at", "content", "tags", "pubkey"]:
        assert field in actual, f"missing field {field} in lineage event"
        assert actual[field] == expected[field]
