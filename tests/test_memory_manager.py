import os
import shutil
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.memory_manager import MemoryManager
from app.utils.session_tree import SessionTree


def test_memory_manager_flat_history():
    """Test saving and loading a flat chat history list, ensuring think blocks are stripped."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(sessions_dir=temp_dir)
        
        flat_history = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello Karl"},
            {"role": "assistant", "content": "<think>\nThinking about greetings...\n</think>\nHello user! How can I help?"}
        ]
        
        sys_prompt = "Initial system prompt"
        filename = manager.save_session(flat_history, sys_prompt, filename="test_flat.json")
        assert filename == "test_flat.json"
        
        # Load and verify
        loaded_sys, loaded_history = manager.load_session("test_flat.json")
        assert loaded_sys == sys_prompt
        
        # When flat list is loaded, memory_manager converts it to a SessionTree.
        # We walk the active path and verify content.
        active_path = loaded_history.get_active_path()
        assert len(active_path) == 3
        
        # Verify first message (system)
        assert active_path[0].role == "system"
        assert active_path[0].content == "System prompt"
        
        # Verify assistant message (thoughts should be stripped)
        assert active_path[2].role == "assistant"
        assert active_path[2].content == "Hello user! How can I help?"
        
        # Verify files list
        sessions = manager.list_sessions()
        assert "test_flat.json" in sessions
        
    finally:
        shutil.rmtree(temp_dir)


def test_memory_manager_tree_history():
    """Test saving and loading hierarchical SessionTree history, ensuring think blocks are stripped."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(sessions_dir=temp_dir)
        
        # Build tree structure
        tree = SessionTree()
        tree.add_message("user", "Question 1")
        u1_id = tree.current_id
        
        tree.add_message("assistant", "<think>\nDoing some analysis...\n</think>\nAnswer A")
        tree.current_node.thought = "Doing some analysis..."
        a_id = tree.current_id
        
        # Branch back to user message and create Answer B
        tree.set_current_node(u1_id)
        tree.add_message("assistant", "<think>\nDifferent thoughts...\n</think>\nAnswer B")
        tree.current_node.thought = "Different thoughts..."
        b_id = tree.current_id
        
        filename = manager.save_session(tree, "Tree system prompt", filename="test_tree.json")
        
        # Load and verify
        loaded_sys, loaded_tree = manager.load_session(filename)
        assert loaded_sys == "Tree system prompt"
        assert isinstance(loaded_tree, SessionTree)
        
        # Verify that loaded tree contains both branches and thoughts are stripped from content
        node_a = loaded_tree.nodes_map.get(a_id)
        node_b = loaded_tree.nodes_map.get(b_id)
        
        assert node_a is not None
        assert node_b is not None
        
        # Core text content should be stripped of thoughts
        assert node_a.content == "Answer A"
        assert node_b.content == "Answer B"
        
        # The separate thought fields should be preserved
        assert node_a.thought == "Doing some analysis..."
        assert node_b.thought == "Different thoughts..."
        
        # Parent-child mapping checks
        assert node_a.parent.id == u1_id
        assert node_b.parent.id == u1_id
        
    finally:
        shutil.rmtree(temp_dir)
