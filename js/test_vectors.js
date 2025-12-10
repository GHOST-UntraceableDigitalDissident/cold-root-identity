const assert = require("assert");
const path = require("path");
const fs = require("fs");

const { deriveEpochKey, makeLineageEvent, verifyLineage } = require("./coldroot");

function loadVectors() {
  const p = path.join(__dirname, "..", "tests", "vectors", "cold_root_identity.v1.json");
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function testEpochVector() {
  const data = loadVectors();
  const root = data.root;
  const epoch = data.epochs.find(e => e.id === "epoch-2025-Q1");

  const derived = deriveEpochKey(root.sk_hex, epoch.label);

  assert.strictEqual(derived.skSeedHex.toLowerCase(), epoch.sk_hex.toLowerCase());
  assert.strictEqual(derived.pkHex.toLowerCase(), epoch.pk_hex.toLowerCase());

  console.log("✓ JS epoch derivation matches vectors");
}

function testLineageEvent() {
  const data = loadVectors();
  const root = data.root;
  const epoch = data.epochs.find(e => e.id === "epoch-2025-Q1");
  const expected = epoch.lineage_event;

  const event = makeLineageEvent(
    root.sk_hex,
    epoch.pk_hex,
    epoch.label,
    expected.kind,
    expected.created_at
  );

  assert.strictEqual(event.kind, expected.kind);
  assert.strictEqual(event.created_at, expected.created_at);
  assert.strictEqual(event.pubkey.toLowerCase(), expected.pubkey.toLowerCase());
  assert.strictEqual(JSON.stringify(event.tags), JSON.stringify(expected.tags));

  const rootPubHex = expected.tags.find(t => t[0] === "root")[1];
  assert.ok(verifyLineage(rootPubHex, event));

  console.log("✓ JS lineage event matches vectors and verifies");
}

testEpochVector();
testLineageEvent();

console.log("All JS tests passed.");
