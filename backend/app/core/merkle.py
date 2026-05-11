import hashlib


def _hash_pair(left: str, right: str) -> str:
    """SHA-256 of left_bytes || right_bytes (position-ordered, not sorted)."""
    combined = bytes.fromhex(left) + bytes.fromhex(right)
    return hashlib.sha256(combined).hexdigest()


def build_merkle_tree(leaf_hashes: list[str]) -> tuple[str, list[list[dict]]]:
    """
    Build a binary Merkle tree from SHA-256 leaf hashes.

    Returns:
        root_hash  — the Merkle root (hex string)
        proof_paths — proof_paths[i] is the proof path for leaf i.
                      Each step is {"hash": "<hex>", "position": "left"|"right"}
                      where "position" is the side of the SIBLING node.
    """
    if not leaf_hashes:
        empty = hashlib.sha256(b"").hexdigest()
        return empty, []

    if len(leaf_hashes) == 1:
        return leaf_hashes[0], [[]]

    n = len(leaf_hashes)
    current_level: list[str] = list(leaf_hashes)
    # Map: original leaf index -> current position in the working level
    leaf_pos = list(range(n))
    proof_paths: list[list[dict]] = [[] for _ in range(n)]

    while len(current_level) > 1:
        # Pad odd-length levels by duplicating the last node
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        next_level: list[str] = []
        next_leaf_pos = list(leaf_pos)

        for pair_start in range(0, len(current_level), 2):
            left = current_level[pair_start]
            right = current_level[pair_start + 1]
            parent = _hash_pair(left, right)
            next_level.append(parent)

            pair_idx = pair_start // 2

            for orig_idx in range(n):
                if leaf_pos[orig_idx] == pair_start:
                    # This leaf is on the left — sibling is on the right
                    proof_paths[orig_idx].append({"hash": right, "position": "right"})
                    next_leaf_pos[orig_idx] = pair_idx
                elif leaf_pos[orig_idx] == pair_start + 1:
                    # This leaf is on the right — sibling is on the left
                    proof_paths[orig_idx].append({"hash": left, "position": "left"})
                    next_leaf_pos[orig_idx] = pair_idx

        leaf_pos = next_leaf_pos
        current_level = next_level

    return current_level[0], proof_paths


def verify_inclusion(leaf_hash: str, proof_path: list[dict], root: str) -> bool:
    """
    Verify a Merkle proof path.

    Args:
        leaf_hash  — SHA-256 hex of the file content
        proof_path — list of {"hash": "<hex>", "position": "left"|"right"}
                     steps from leaf to root
        root       — expected Merkle root (hex string)

    Returns True if the proof is valid.
    """
    node = leaf_hash
    for step in proof_path:
        sibling = step["hash"]
        if step["position"] == "left":
            # Sibling on the left, current node on the right
            node = _hash_pair(sibling, node)
        else:
            # Sibling on the right, current node on the left
            node = _hash_pair(node, sibling)
    return node == root
