package coldroot_test

import (
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"

	coldroot "github.com/GHOST-UntraceableDigitalDissident/cold-root-identity/go"
	"crypto/ed25519"
)

type rootJSON struct {
	ID      string  `json:"id"`
	SeedHex string  `json:"seed_hex"`
	SKHex   string  `json:"sk_hex"`
	PKHex   string  `json:"pk_hex"`
	Nsec    *string `json:"nsec"`
	Npub    *string `json:"npub"`
}

type lineageEventJSON struct {
	Kind      int        `json:"kind"`
	CreatedAt int64      `json:"created_at"`
	Pubkey    string     `json:"pubkey"`
	Tags      [][]string `json:"tags"`
	Content   string     `json:"content"`
	ID        *string    `json:"id"`
	Sig       *string    `json:"sig"`
}

type epochJSON struct {
	ID           string           `json:"id"`
	Label        string           `json:"label"`
	SKHex        string           `json:"sk_hex"`
	PKHex        string           `json:"pk_hex"`
	Npub         *string          `json:"npub"`
	LineageEvent lineageEventJSON `json:"lineage_event"`
}

type vectorsJSON struct {
	SpecVersion string      `json:"spec_version"`
	Language    string      `json:"language"`
	Description string      `json:"description"`
	Root        rootJSON    `json:"root"`
	Epochs      []epochJSON `json:"epochs"`
}

func loadVectors(t *testing.T) vectorsJSON {
	t.Helper()
	path := filepath.Join("..", "tests", "vectors", "cold_root_identity.v1.json")

	data, err := os.ReadFile(path)
	require.NoError(t, err)

	var v vectorsJSON
	err = json.Unmarshal(data, &v)
	require.NoError(t, err)

	return v
}

func TestRootVector(t *testing.T) {
	v := loadVectors(t)
	root := v.Root

	seed, err := hex.DecodeString(root.SeedHex)
	require.NoError(t, err)

	rootSK, err := coldroot.SeedToRootKey(seed)
	require.NoError(t, err)
	require.Equal(t, root.SKHex, hex.EncodeToString(rootSK))

	rootPK, err := coldroot.RootPublicKey(rootSK)
	require.NoError(t, err)
	require.Equal(t, root.PKHex, hex.EncodeToString(rootPK))
}

func TestEpoch2025Q1Vector(t *testing.T) {
	v := loadVectors(t)
	root := v.Root

	var epoch epochJSON
	for _, e := range v.Epochs {
		if e.ID == "epoch-2025-Q1" {
			epoch = e
			break
		}
	}

	rootSeedHex := root.SeedHex

	sk, pk, err := coldroot.DeriveEpochKey(rootSeedHex, epoch.Label)
	require.NoError(t, err)

	require.Equal(t, epoch.PKHex, hex.EncodeToString(pk))
	require.Equal(t, epoch.SKHex, hex.EncodeToString(sk[:32])) // first 32 bytes = seed
}

func TestEpoch2025Q1LineageEvent(t *testing.T) {
	v := loadVectors(t)
	root := v.Root

	var epoch epochJSON
	for _, e := range v.Epochs {
		if e.ID == "epoch-2025-Q1" {
			epoch = e
			break
		}
	}

	rootSeed, _ := hex.DecodeString(root.SeedHex)
	rootPriv := ed25519.NewKeyFromSeed(rootSeed)

	epochPKBytes, _ := hex.DecodeString(epoch.PKHex)
	createdAt, err := coldroot.DeterministicCreatedAt(epoch.Label)
	require.NoError(t, err)

	ev := coldroot.MakeLineageEvent(
		rootPriv,
		ed25519.PublicKey(epochPKBytes),
		epoch.Label,
		epoch.LineageEvent.Kind,
		createdAt,
	)

	require.Equal(t, epoch.LineageEvent.Kind, ev.Kind)
	require.Equal(t, epoch.LineageEvent.CreatedAt, ev.CreatedAt)
	require.Equal(t, epoch.LineageEvent.Content, ev.Content)
	require.Equal(t, epoch.LineageEvent.Pubkey, ev.Pubkey)
	require.Equal(t, epoch.LineageEvent.Tags, ev.Tags)
}

