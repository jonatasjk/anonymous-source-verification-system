"""Unit tests for app.core.merkle."""
import hashlib
import pytest

from app.core.merkle import build_merkle_tree, verify_inclusion, _hash_pair


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


LEAF_A = _sha256(b"a")
LEAF_B = _sha256(b"b")
LEAF_C = _sha256(b"c")
LEAF_D = _sha256(b"d")


# ---------------------------------------------------------------------------
# _hash_pair
# ---------------------------------------------------------------------------

def test_hash_pair_is_sha256_of_concatenation():
    left = "aabb"
    right = "ccdd"
    expected = hashlib.sha256(bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()
    assert _hash_pair(left, right) == expected


def test_hash_pair_not_commutative():
    assert _hash_pair(LEAF_A, LEAF_B) != _hash_pair(LEAF_B, LEAF_A)


# ---------------------------------------------------------------------------
# build_merkle_tree — edge cases
# ---------------------------------------------------------------------------

def test_empty_leaf_list():
    root, paths = build_merkle_tree([])
    assert root == hashlib.sha256(b"").hexdigest()
    assert paths == []


def test_single_leaf():
    root, paths = build_merkle_tree([LEAF_A])
    assert root == LEAF_A
    assert paths == [[]]


# ---------------------------------------------------------------------------
# build_merkle_tree — 2 leaves (power of two)
# ---------------------------------------------------------------------------

def test_two_leaves_root():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B])
    expected_root = _hash_pair(LEAF_A, LEAF_B)
    assert root == expected_root


def test_two_leaves_proof_paths_structure():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B])
    assert len(paths) == 2
    # Leaf 0 is on the left; sibling is LEAF_B on the right
    assert paths[0] == [{"hash": LEAF_B, "position": "right"}]
    # Leaf 1 is on the right; sibling is LEAF_A on the left
    assert paths[1] == [{"hash": LEAF_A, "position": "left"}]


def test_two_leaves_proofs_verify():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B])
    assert verify_inclusion(LEAF_A, paths[0], root)
    assert verify_inclusion(LEAF_B, paths[1], root)


# ---------------------------------------------------------------------------
# build_merkle_tree — 3 leaves (odd, requires padding)
# ---------------------------------------------------------------------------

def test_three_leaves_root():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B, LEAF_C])
    # Level 1: [hash(A,B), hash(C,C)]   (C padded with itself)
    ab = _hash_pair(LEAF_A, LEAF_B)
    cc = _hash_pair(LEAF_C, LEAF_C)
    expected = _hash_pair(ab, cc)
    assert root == expected


def test_three_leaves_proofs_verify():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B, LEAF_C])
    for i, leaf in enumerate([LEAF_A, LEAF_B, LEAF_C]):
        assert verify_inclusion(leaf, paths[i], root), f"Proof for leaf {i} failed"


# ---------------------------------------------------------------------------
# build_merkle_tree — 4 leaves (perfect binary tree)
# ---------------------------------------------------------------------------

def test_four_leaves_proofs_verify():
    leaves = [LEAF_A, LEAF_B, LEAF_C, LEAF_D]
    root, paths = build_merkle_tree(leaves)
    for i, leaf in enumerate(leaves):
        assert verify_inclusion(leaf, paths[i], root), f"Proof for leaf {i} failed"


def test_four_leaves_root_matches_manual():
    ab = _hash_pair(LEAF_A, LEAF_B)
    cd = _hash_pair(LEAF_C, LEAF_D)
    expected = _hash_pair(ab, cd)
    root, _ = build_merkle_tree([LEAF_A, LEAF_B, LEAF_C, LEAF_D])
    assert root == expected


# ---------------------------------------------------------------------------
# build_merkle_tree — larger sets
# ---------------------------------------------------------------------------

def test_five_leaves_proofs_verify():
    leaves = [_sha256(bytes([i])) for i in range(5)]
    root, paths = build_merkle_tree(leaves)
    for i, leaf in enumerate(leaves):
        assert verify_inclusion(leaf, paths[i], root), f"Proof for leaf {i} failed"


def test_sixteen_leaves_proofs_verify():
    leaves = [_sha256(bytes([i])) for i in range(16)]
    root, paths = build_merkle_tree(leaves)
    for i, leaf in enumerate(leaves):
        assert verify_inclusion(leaf, paths[i], root), f"Proof for leaf {i} failed"


# ---------------------------------------------------------------------------
# verify_inclusion — negative cases
# ---------------------------------------------------------------------------

def test_verify_wrong_root_fails():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B])
    assert not verify_inclusion(LEAF_A, paths[0], "0" * 64)


def test_verify_wrong_leaf_fails():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B])
    assert not verify_inclusion(LEAF_C, paths[0], root)


def test_verify_tampered_proof_fails():
    root, paths = build_merkle_tree([LEAF_A, LEAF_B, LEAF_C])
    tampered = [{"hash": "0" * 64, "position": "right"}]
    assert not verify_inclusion(LEAF_A, tampered, root)


def test_verify_empty_proof_for_single_leaf():
    root, paths = build_merkle_tree([LEAF_A])
    assert verify_inclusion(LEAF_A, [], root)
