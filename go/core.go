package coldroot

import (
    "crypto/ed25519"
    "crypto/sha256"
    "encoding/hex"
    "errors"
    "io"
    "strconv"
    "strings"
    "time"

    "golang.org/x/crypto/hkdf"
)


type LineageEvent struct {
	Kind      int        `json:"kind"`
	CreatedAt int64      `json:"created_at"`
	Pubkey    string     `json:"pubkey"`
	Tags      [][]string `json:"tags"`
	Content   string     `json:"content"`
}

// ----------------------
// Root key model
// ----------------------

func SeedToRootKey(seed []byte) ([]byte, error) {
	if len(seed) != 32 {
		return nil, errors.New("seed must be 32 bytes")
	}
	out := make([]byte, 32)
	copy(out, seed)
	return out, nil
}

func RootPublicKey(rootSK []byte) (ed25519.PublicKey, error) {
	if len(rootSK) != 32 {
		return nil, errors.New("root secret key must be 32 bytes")
	}
	priv := ed25519.NewKeyFromSeed(rootSK)
	pub := priv.Public().(ed25519.PublicKey)
	return pub, nil
}

// ----------------------
// Epoch derivation
// ----------------------

func DeriveEpochKey(rootSeedHex string, label string) (ed25519.PrivateKey, ed25519.PublicKey, error) {
    seed, err := hex.DecodeString(rootSeedHex)
    if err != nil {
        return nil, nil, err
    }
    if len(seed) != 32 {
        return nil, nil, errors.New("root seed must decode to 32 bytes")
    }

    info := []byte("epoch:" + label)
    salt := []byte("nostr-cold-root")

    r := hkdf.New(sha256.New, seed, salt, info)
    childSeed := make([]byte, 32)

    if _, err := io.ReadFull(r, childSeed); err != nil {
        return nil, nil, err
    }

    sk := ed25519.NewKeyFromSeed(childSeed)
    pk := sk.Public().(ed25519.PublicKey)
    return sk, pk, nil
}


// ----------------------
// Deterministic timestamps for references
// ----------------------

func DeterministicCreatedAt(label string) (int64, error) {
	parts := strings.Split(label, "-Q")
	if len(parts) != 2 {
		return 0, errors.New("invalid epoch label: expected YYYY-Qn")
	}

	year, err := strconv.Atoi(parts[0])
	if err != nil {
		return 0, err
	}

	q, err := strconv.Atoi(parts[1])
	if err != nil {
		return 0, err
	}

	if q < 1 || q > 4 {
		return 0, errors.New("quarter must be 1..4")
	}

	month := (q-1)*3 + 1

	t := time.Date(year, time.Month(month), 1, 0, 0, 0, 0, time.UTC)
	return t.Unix(), nil
}

// ----------------------
// Lineage event
// ----------------------

func MakeLineageEvent(
	rootSK ed25519.PrivateKey,
	epochPK ed25519.PublicKey,
	label string,
	kind int,
	createdAt int64,
) LineageEvent {

	rootVK := rootSK.Public().(ed25519.PublicKey)

	sig := ed25519.Sign(rootSK, epochPK)
	rootHex := hex.EncodeToString(rootVK)
	sigHex := hex.EncodeToString(sig)
	epochPubHex := hex.EncodeToString(epochPK)

	tags := [][]string{
		{"root", rootHex},
		{"sig", sigHex},
		{"epoch", label},
	}

	return LineageEvent{
		Kind:      kind,
		CreatedAt: createdAt,
		Pubkey:    epochPubHex,
		Content:   "",
		Tags:      tags,
	}
}
