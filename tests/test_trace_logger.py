import os
import sys
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.utils.trace_logger as tl
from app.utils.trace_logger import TraceLogger

def test_schema_fields():
    print("Testing TraceLogger schema fields...")
    temp_dir = tempfile.mkdtemp()
    try:
        logger = TraceLogger(log_dir=temp_dir)
        log_file = logger.log_generation(
            compiled_prompt="System rules\nUser message",
            hyperparams={"temperature": 0.7, "top_p": 0.9},
            raw_output="Thought response",
            parsed_thought="Thought",
            parsed_response="response",
            execution_time=2.5,
            rag_context=["chunk1"],
            workflow="code_review",
            template="json_extractor",
            feedback="none",
            model_name="qwen-1.5b",
            adapter_name="lora-1"
        )
        
        # Read the logged record
        assert os.path.exists(log_file)
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        record = json.loads(line)
        
        # Verify schema keys
        expected_keys = {
            "id", "session_id", "timestamp", "timing", "model", "adapter",
            "workflow", "template", "hyperparams", "system_prompt",
            "compiled_prompt", "thinking", "response", "raw_output",
            "rag_chunks", "feedback", "corrected_response"
        }
        assert set(record.keys()) == expected_keys, f"Missing or extra keys: {record.keys()}"
        
        # Assert values
        assert record["model"] == "qwen-1.5b"
        assert record["adapter"] == "lora-1"
        assert record["workflow"] == "code_review"
        assert record["template"] == "json_extractor"
        assert record["hyperparams"] == {"temperature": 0.7, "top_p": 0.9}
        assert record["timing"]["total_seconds"] == 2.5
        assert record["thinking"] == "Thought"
        assert record["response"] == "response"
        assert record["rag_chunks"] == ["chunk1"]
        assert record["feedback"] == "none"
        
        # Test updating feedback
        logger.update_last_entry_feedback(feedback="thumbs_up")
        with open(log_file, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        record = json.loads(line)
        assert record["feedback"] == "thumbs_up"
        
        print("TraceLogger schema fields OK.")
    finally:
        shutil.rmtree(temp_dir)

def test_file_rotation():
    print("Testing TraceLogger rotation logic...")
    temp_dir = tempfile.mkdtemp()
    
    # Save original max bytes
    old_max = tl._MAX_BYTES
    # Set max bytes very small so any entry triggers rotation
    tl._MAX_BYTES = 50 
    
    try:
        logger = TraceLogger(log_dir=temp_dir)
        
        # Write one entry. This file will exceed 50 bytes.
        file1 = logger.log_generation("prompt 1", {}, "raw 1", "thought 1", "resp 1", 1.0)
        
        # Next entry should be written to rotated file
        file2 = logger.log_generation("prompt 2", {}, "raw 2", "thought 2", "resp 2", 1.0)
        
        assert file1 != file2, f"Expected rotation, but both wrote to {file1}"
        assert os.path.exists(file1)
        assert os.path.exists(file2)
        
        # Verify contents of both
        with open(file1, "r") as f:
            r1 = json.loads(f.readline().strip())
        with open(file2, "r") as f:
            r2 = json.loads(f.readline().strip())
            
        assert r1["thinking"] == "thought 1"
        assert r2["thinking"] == "thought 2"
        
        print("TraceLogger rotation OK.")
    finally:
        tl._MAX_BYTES = old_max
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_schema_fields()
    test_file_rotation()
    print("All trace logger unit tests PASSED!")
