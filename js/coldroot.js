// js/coldroot.js
// Cold Root Identity JS reference implementation (Node)

const crypto = require("crypto");
const nacl = require("tweetnacl");

// ---------- HKDF-SHA256 ----------

function hkdfSha256(ikm, salt, info, length) {
  const hashLen = 32;
  if (length > 255 * hashLen) {
    throw new Error("hkdfSha256: length too large");
  }

  const prk = crypto.createHmac("sha256", salt).update(ikm).digest();

  let t = Buffer.alloc(0);
  let okm = Buffer.alloc(0);

  const n = Math.ceil(length / hashLen);

  for (let i = 1; i <= n; i++) {
    t = crypto
      .createHmac("sha256", prk)
      .update(Buffer.concat([t, info, Buffer.from([i])]))
      .digest();
    okm = Buffer.concat([okm, t]);
  }

  return okm.slice(0, length);
}

// HKDF parameters (must match SPEC.md)
const HKDF_SALT = Buffer.from("nostr-cold-root", "utf8");

// ---------- Core derivation ----------

function deriveEpochKey(rootSeedHex, epochLabel) {
  const rootSeed = Buffer.from(rootSeedHex, "hex");
  if (rootSeed.length !== 32) {
    throw new Error("root seed must be 32 bytes (64 hex chars)");
  }

  const info = Buffer.concat([
    Buffer.from("epoch:", "utf8"),
    Buffer.from(epochLabel, "utf8"),
  ]);

  const childSeed = hkdfSha256(rootSeed, HKDF_SALT, info, 32);

  // tweetnacl uses a 32-byte seed for keypair
  const kp = nacl.sign.keyPair.fromSeed(childSeed);

  // skSeedHex is the 32-byte seed, pkHex is 32-byte pubkey
  return {
    skSeedHex: Buffer.from(childSeed).toString("hex"),
    pkHex: Buffer.from(kp.publicKey).toString("hex"),
    secretKey: kp.secretKey, // 64 bytes, internal use
  };
}

function rootKeyPairFromSeedHex(rootSeedHex) {
  const rootSeed = Buffer.from(rootSeedHex, "hex");
  if (rootSeed.length !== 32) {
    throw new Error("root seed must be 32 bytes (64 hex chars)");
  }
  const kp = nacl.sign.keyPair.fromSeed(rootSeed);
  return {
    pubKey: Buffer.from(kp.publicKey),
    secretKey: kp.secretKey, // 64 bytes
  };
}

// ---------- Lineage event ----------

function makeLineageEvent(
  rootSeedHex,
  epochPkHex,
  epochLabel,
  kind = 30001,
  createdAt
) {
  const { pubKey: rootPub, secretKey: rootSk } =
    rootKeyPairFromSeedHex(rootSeedHex);
  const epochPub = Buffer.from(epochPkHex, "hex");

  const sig = Buffer.from(nacl.sign.detached(epochPub, rootSk));
  const ts = createdAt != null ? createdAt : Math.floor(Date.now() / 1000);

  return {
    kind: kind,
    pubkey: epochPub.toString("hex"),
    created_at: ts,
    tags: [
      ["root", rootPub.toString("hex")],
      ["sig", sig.toString("hex")],
      ["epoch", epochLabel],
    ],
    content: "",
  };
}

// Extract root/sig/epoch from tags; internal helper
function extractLineageTags(event) {
  let rootHex = null;
  let sigHex = null;
  let epochLabel = null;

  for (const tag of event.tags || []) {
    if (!Array.isArray(tag) || tag.length < 2) continue;
    if (tag[0] === "root") rootHex = tag[1];
    else if (tag[0] === "sig") sigHex = tag[1];
    else if (tag[0] === "epoch") epochLabel = tag[1];
  }

  return { rootHex, sigHex, epochLabel };
}

// ---------- Verification ----------

function verifyLineage(rootPubkeyHex, event) {
  if (!event || typeof event !== "object") return false;

  const { rootHex, sigHex } = extractLineageTags(event);
  if (!rootHex || !sigHex) return false;

  // root tag must match the claimed root pubkey
  if (rootHex.toLowerCase() !== rootPubkeyHex.toLowerCase()) return false;

  const epochPub = Buffer.from(event.pubkey, "hex");
  const sig = Buffer.from(sigHex, "hex");
  const rootPub = Buffer.from(rootPubkeyHex, "hex");

  return nacl.sign.detached.verify(epochPub, sig, rootPub);
}

module.exports = {
  deriveEpochKey,
  makeLineageEvent,
  verifyLineage,
};
