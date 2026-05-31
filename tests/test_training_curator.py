import os
import sys
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.utils.training_curator as tc
from app.utils.training_curator import TrainingCurator

def test_curation_saving_and_sft_export():
    print("Testing curator save & SFT export...")
    temp_dir = tempfile.mkdtemp()
    
    old_path = tc.CURATED_PATH
    tc.CURATED_PATH = os.path.join(temp_dir, "curated.jsonl")
    
    try:
        curator = TrainingCurator()
        
        # Save a couple of examples
        curator.save_example(prompt="User prompt 1", response="Karl response 1", source="thumbs_up", system_prompt="Sys 1")
        curator.save_example(prompt="User prompt 2", response="Karl response 2", source="corrected", system_prompt="Sys 2")
        
        # Verify stats
        stats = curator.get_stats()
        assert stats["total"] == 2
        assert stats["thumbs_up"] == 1
        assert stats["corrected"] == 1
        
        # Export SFT format
        export_file = os.path.join(temp_dir, "export_sft.jsonl")
        res_path = curator.export_unsloth(export_file)
        assert res_path == export_file
        assert os.path.exists(export_file)
        
        # Verify SFT structure (only the 'messages' field)
        with open(export_file, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2
        
        ex1 = json.loads(lines[0].strip())
        assert "messages" in ex1
        assert len(ex1["messages"]) == 3
        assert ex1["messages"][0]["role"] == "system"
        assert ex1["messages"][0]["content"] == "Sys 1"
        assert ex1["messages"][1]["role"] == "user"
        assert ex1["messages"][1]["content"] == "User prompt 1"
        assert ex1["messages"][2]["role"] == "assistant"
        assert ex1["messages"][2]["content"] == "Karl response 1"
        
        # Test deletion
        curator.delete_example(0)
        assert curator.get_stats()["total"] == 1
        
        print("Curator SFT export and stats OK.")
    finally:
        tc.CURATED_PATH = old_path
        shutil.rmtree(temp_dir)

def test_curator_dpo_pairing():
    print("Testing curator DPO pairing...")
    temp_dir = tempfile.mkdtemp()
    
    old_path = tc.CURATED_PATH
    tc.CURATED_PATH = os.path.join(temp_dir, "curated.jsonl")
    
    try:
        curator = TrainingCurator()
        
        # Add a matching pair (chosen + rejected)
        curator.save_example(prompt="prompt A", response="chosen A", source="thumbs_up", system_prompt="sys A")
        curator.save_example(prompt="prompt A", response="rejected A", source="thumbs_down", system_prompt="sys A")
        
        # Add another matching pair
        curator.save_example(prompt="prompt B", response="chosen B", source="corrected", system_prompt="sys B")
        curator.save_example(prompt="prompt B", response="rejected B", source="thumbs_down", system_prompt="sys B")
        
        # Add unmatched entries
        curator.save_example(prompt="unmatched chosen", response="chosen C", source="thumbs_up", system_prompt="sys C")
        curator.save_example(prompt="unmatched rejected", response="rejected D", source="thumbs_down", system_prompt="sys D")
        
        # Export DPO
        export_file = os.path.join(temp_dir, "export_dpo.jsonl")
        res_path = curator.export_dpo(export_file)
        assert res_path == export_file
        
        # Read pairs
        pairs = []
        with open(export_file, "r") as f:
            for line in f:
                pairs.append(json.loads(line.strip()))
                
        # Expect 2 pairs
        assert len(pairs) == 2, f"Expected 2 pairs, got {len(pairs)}"
        
        # Validate values of first pair
        p1 = [p for p in pairs if p["prompt"][1]["content"] == "prompt A"][0]
        assert p1["chosen"][0]["content"] == "chosen A"
        assert p1["rejected"][0]["content"] == "rejected A"
        assert p1["prompt"][0]["content"] == "sys A"
        
        # Validate values of second pair
        p2 = [p for p in pairs if p["prompt"][1]["content"] == "prompt B"][0]
        assert p2["chosen"][0]["content"] == "chosen B"
        assert p2["rejected"][0]["content"] == "rejected B"
        assert p2["prompt"][0]["content"] == "sys B"
        
        print("Curator DPO pairing OK.")
    finally:
        tc.CURATED_PATH = old_path
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_curation_saving_and_sft_export()
    test_curator_dpo_pairing()
    print("All training curator unit tests PASSED!")
