import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.session_tree import SessionNode, SessionTree


# ---------------------------------------------------------------------------
# SessionNode tests
# ---------------------------------------------------------------------------

def test_node_defaults():
    node = SessionNode("user", "hello")
    assert node.role == "user"
    assert node.content == "hello"
    assert node.id is not None
    assert node.children == []
    assert node.parent is None
    assert node.thought is None


def test_node_add_child():
    parent = SessionNode("user", "hi")
    child = parent.add_child("assistant", "hey")
    assert child in parent.children
    assert child.parent is parent
    assert child.role == "assistant"


def test_node_to_from_dict_round_trip():
    parent = SessionNode("user", "question", node_id="u1")
    child = parent.add_child("assistant", "answer", node_id="a1")
    child.thought = "thinking..."

    data = parent.to_dict()
    restored = SessionNode.from_dict(data)

    assert restored.id == "u1"
    assert restored.content == "question"
    assert len(restored.children) == 1
    assert restored.children[0].id == "a1"
    assert restored.children[0].thought == "thinking..."


def test_node_attachments_round_trip():
    node = SessionNode(
        "user",
        "what is wrong here?",
        node_id="img1",
        attachments=[{"type": "image", "id": "abc", "path": "data/images/inbox/abc.png"}],
    )
    restored = SessionNode.from_dict(node.to_dict())
    assert restored.attachments[0]["type"] == "image"
    assert restored.attachments[0]["id"] == "abc"


# ---------------------------------------------------------------------------
# SessionTree tests
# ---------------------------------------------------------------------------

def test_tree_empty_on_init():
    tree = SessionTree()
    assert len(tree) == 0
    assert not tree  # __bool__


def test_tree_add_message():
    tree = SessionTree()
    tree.add_message("user", "Hello")
    tree.add_message("assistant", "Hi there")
    path = tree.get_active_path()
    assert len(path) == 2
    assert path[0].role == "user"
    assert path[1].role == "assistant"


def test_tree_active_path_content():
    tree = SessionTree()
    tree.add_message("user", "Q1", attachments=[{"type": "image", "id": "abc"}])
    tree.add_message("assistant", "A1")
    dicts = tree.get_active_path_dicts()
    assert dicts[0]["content"] == "Q1"
    assert dicts[0]["attachments"][0]["id"] == "abc"
    assert dicts[1]["content"] == "A1"
    assert "id" in dicts[0]


def test_tree_branching():
    """Branch from a node and verify two separate paths exist."""
    tree = SessionTree()
    tree.add_message("user", "Root question")
    root_user_id = tree.current_id

    # Path A
    tree.add_message("assistant", "Answer A")
    path_a_id = tree.current_id

    # Branch back to root user message
    tree.set_current_node(root_user_id)
    tree.add_message("assistant", "Answer B")
    path_b_id = tree.current_id

    # Navigate to path A
    tree.set_current_node(path_a_id)
    path_a = tree.get_active_path()
    assert path_a[-1].content == "Answer A"

    # Navigate to path B
    tree.set_current_node(path_b_id)
    path_b = tree.get_active_path()
    assert path_b[-1].content == "Answer B"

    # Both paths share root user message
    assert path_a[0].id == path_b[0].id


def test_tree_serialization_round_trip():
    tree = SessionTree()
    tree.add_message("user", "ping")
    tree.add_message("assistant", "pong")
    saved_id = tree.current_id

    data = tree.to_dict()
    restored = SessionTree.from_dict(data)

    assert restored.current_id == saved_id
    path = restored.get_active_path()
    assert len(path) == 2
    assert path[0].content == "ping"
    assert path[1].content == "pong"


def test_tree_serialization_with_branch():
    tree = SessionTree()
    tree.add_message("user", "base")
    base_id = tree.current_id

    tree.add_message("assistant", "branch A")

    tree.set_current_node(base_id)
    tree.add_message("assistant", "branch B")
    b_id = tree.current_id

    data = tree.to_dict()
    restored = SessionTree.from_dict(data)
    restored.set_current_node(b_id)
    path = restored.get_active_path()
    assert path[-1].content == "branch B"


def test_tree_clear():
    tree = SessionTree()
    tree.add_message("user", "hi")
    tree.add_message("assistant", "hello")
    tree.clear()
    assert len(tree) == 0


def test_tree_copy_is_independent():
    tree = SessionTree()
    tree.add_message("user", "original")
    copy = tree.copy()
    copy.add_message("assistant", "added in copy")
    # Original should be unaffected
    assert len(tree) == 1
    assert len(copy) == 2


def test_tree_duck_typing_len_iter():
    tree = SessionTree()
    tree.add_message("user", "a")
    tree.add_message("assistant", "b")
    tree.add_message("user", "c")

    assert len(tree) == 3
    items = list(tree)
    assert items[0]["role"] == "user"
    assert items[2]["content"] == "c"


def test_tree_getitem():
    tree = SessionTree()
    tree.add_message("user", "first")
    tree.add_message("assistant", "second")
    assert tree[0]["content"] == "first"
    assert tree[1]["content"] == "second"
    assert tree[-1]["content"] == "second"


def test_tree_append_dict():
    tree = SessionTree()
    tree.append({"role": "user", "content": "via append"})
    tree.append({"role": "assistant", "content": "reply"})
    assert len(tree) == 2
    assert tree[0]["content"] == "via append"


def test_tree_append_invalid_raises():
    tree = SessionTree()
    try:
        tree.append({"role": "user"})  # missing "content"
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_tree_update_current_node_content():
    tree = SessionTree()
    node = tree.add_message("assistant", "draft")
    tree.update_current_node_content("final answer")
    assert tree.current_node.content == "final answer"


def test_tree_nodes_map_consistency():
    """nodes_map must contain every node after tree operations."""
    tree = SessionTree()
    tree.add_message("user", "x")
    uid = tree.current_id
    tree.add_message("assistant", "y")
    tree.set_current_node(uid)
    tree.add_message("assistant", "z")

    # Every node should be in the map
    def collect(node, ids):
        ids.add(node.id)
        for c in node.children:
            collect(c, ids)

    all_ids = set()
    collect(tree.root, all_ids)
    for nid in all_ids:
        assert nid in tree.nodes_map, f"Node {nid} missing from nodes_map"


def test_tree_stats_and_branch_label():
    tree = SessionTree()
    user = tree.add_message("user", "base")
    tree.add_message("assistant", "branch A")
    tree.branch_from(user.id, "assistant", "branch B")

    stats = tree.stats()
    assert stats.message_nodes == 3
    assert stats.leaf_count == 2
    assert stats.max_depth == 2
    assert tree.active_branch_label().startswith("assistant:")


def test_branch_from_missing_returns_none():
    tree = SessionTree()
    assert tree.branch_from("missing", "user", "nope") is None
    assert len(tree) == 0


if __name__ == "__main__":
    test_node_defaults()
    test_node_add_child()
    test_node_to_from_dict_round_trip()
    test_node_attachments_round_trip()
    test_tree_empty_on_init()
    test_tree_add_message()
    test_tree_active_path_content()
    test_tree_branching()
    test_tree_serialization_round_trip()
    test_tree_serialization_with_branch()
    test_tree_clear()
    test_tree_copy_is_independent()
    test_tree_duck_typing_len_iter()
    test_tree_getitem()
    test_tree_append_dict()
    test_tree_append_invalid_raises()
    test_tree_update_current_node_content()
    test_tree_nodes_map_consistency()
    print("All session_tree unit tests PASSED!")
