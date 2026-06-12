import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.model_loader import ModelLoader
from eval.harness import EvalHarness

class MockLlama:
    def tokenize(self, text_bytes, add_bos=True):
        return [0] * (len(text_bytes) // 4 + 1)
        
    def __call__(self, prompt, **kwargs):
        if "electronics" in prompt:
            return {"choices": [{"text": "<think>thinking</think>The return window is 15 days."}]}
        if "CEO of Meridian" in prompt:
            return {"choices": [{"text": "<think>thinking</think>Sandra Holt is the CEO."}]}
        return {"choices": [{"text": "<think>thinking</think>unrelated response"}]}


def test_eval_harness_model_and_adapter_selection():
    print("Testing EvalHarness model and adapter selection...")
    
    # Save original ModelLoader attributes to restore later
    orig_get_instance = ModelLoader.get_instance
    orig_model_name = ModelLoader.model_name
    orig_n_ctx = ModelLoader.n_ctx

    mock_llama = MockLlama()
    get_instance_calls = []

    def mock_get_instance(model_path=None, adapter_name=None):
        get_instance_calls.append((model_path, adapter_name))
        return mock_llama

    ModelLoader.get_instance = mock_get_instance
    ModelLoader.model_name = lambda: "mock-model.gguf"
    ModelLoader.n_ctx = lambda: 4096

    # Create temporary dataset
    temp_dir = tempfile.mkdtemp()
    dataset_path = os.path.join(temp_dir, "test_dataset.jsonl")
    
    cases = [
        {"id": "test_001", "prompt": "What is the return policy for electronics?", "expected": "15 days", "grader": "keyword_hit", "keywords": ["15 days"], "require_all": True},
        {"id": "test_002", "prompt": "Who is the CEO of Meridian Technologies?", "expected": "Sandra Holt", "grader": "keyword_hit", "keywords": ["Sandra Holt"], "require_all": True}
    ]
    
    try:
        with open(dataset_path, "w", encoding="utf-8") as f:
            for c in cases:
                f.write(json.dumps(c) + "\n")
                
        harness = EvalHarness()
        
        # Run evaluation with a specific model and adapter override
        report = harness.run(
            dataset_path=dataset_path,
            workflow_name="grounded_answer",
            model_name="deepseek-r1-llama-8b.gguf",
            adapter_name="llama_8b_math_greeting"
        )
        
        # Verify call counts and parameters in ModelLoader
        assert len(get_instance_calls) > 0, "ModelLoader.get_instance should be called"
        # The first call is inside the run guard; subsequent ones are in the _run_model method
        for path, adapter in get_instance_calls:
            assert path is not None and "deepseek-r1-llama-8b.gguf" in path, f"Expected deepseek-r1-llama-8b.gguf, got {path}"
            assert adapter == "llama_8b_math_greeting", f"Expected llama_8b_math_greeting, got {adapter}"
            
        # Verify evaluation report metrics
        assert report.total == 2, f"Expected 2 total cases, got {report.total}"
        assert report.passed == 2, f"Expected 2 passed cases, got {report.passed}"
        assert report.failed == 0
        assert report.pass_rate == 1.0
        
        # Verify individual case results
        assert report.cases[0].case_id == "test_001"
        assert report.cases[0].grade["passed"] is True
        assert report.cases[1].case_id == "test_002"
        assert report.cases[1].grade["passed"] is True
        
        print("EvalHarness model and adapter selection tests PASSED!")
        
    finally:
        # Restore ModelLoader state
        ModelLoader.get_instance = orig_get_instance
        ModelLoader.model_name = orig_model_name
        ModelLoader.n_ctx = orig_n_ctx
        shutil.rmtree(temp_dir)


def test_eval_harness_failure_curation():
    print("Testing EvalHarness failure curation...")
    from eval.harness import EvalHarness
    from app.engine.model_loader import ModelLoader
    import app.utils.training_curator as tc
    
    # Save original states
    orig_get_instance = ModelLoader.get_instance
    orig_model_name = ModelLoader.model_name
    orig_n_ctx = ModelLoader.n_ctx
    orig_curated_path = tc.CURATED_PATH
    
    temp_dir = tempfile.mkdtemp()
    tc.CURATED_PATH = os.path.join(temp_dir, "curated_eval_test.jsonl")
    dataset_path = os.path.join(temp_dir, "dataset.jsonl")
    
    class FailingMockLlama:
        def tokenize(self, text_bytes, add_bos=True):
            return [0]
        def __call__(self, prompt, **kwargs):
            return {"choices": [{"text": "<think>thinking</think>bad response output"}]}
            
    ModelLoader.get_instance = lambda **kwargs: FailingMockLlama()
    ModelLoader.model_name = lambda: "mock.gguf"
    ModelLoader.n_ctx = lambda: 4096
    
    case = {"id": "test_failed", "prompt": "Who wrote Hamlet?", "expected": "Shakespeare", "grader": "keyword_hit", "keywords": ["Shakespeare"], "require_all": True}
    
    try:
        with open(dataset_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(case) + "\n")
            
        harness = EvalHarness()
        report = harness.run(dataset_path=dataset_path, workflow_name="general_chat")
        
        # Verify case failed
        assert report.total == 1
        assert report.passed == 0
        assert report.failed == 1
        
        # Verify curated examples
        examples = tc.get_all_examples()
        assert len(examples) == 2, f"Expected 2 entries, got {len(examples)}"
        
        e_chosen = [e for e in examples if e["source"] == "eval_chosen"][0]
        e_rejected = [e for e in examples if e["source"] == "eval_rejected"][0]
        
        assert e_chosen["messages"][2]["content"] == "Shakespeare"
        assert e_rejected["messages"][2]["content"] == "bad response output"
        assert e_chosen["messages"][1]["content"] == "Who wrote Hamlet?"
        assert e_rejected["messages"][1]["content"] == "Who wrote Hamlet?"
        
        # Verify DPO export works for these
        dpo_file = os.path.join(temp_dir, "dpo.jsonl")
        tc.export_dpo(dpo_file)
        
        with open(dpo_file, "r") as f:
            dpo_lines = f.readlines()
        assert len(dpo_lines) == 1
        dpo_pair = json.loads(dpo_lines[0].strip())
        assert dpo_pair["chosen"][0]["content"] == "Shakespeare"
        assert dpo_pair["rejected"][0]["content"] == "bad response output"
        
        print("EvalHarness failure curation PASSED!")
    finally:
        ModelLoader.get_instance = orig_get_instance
        ModelLoader.model_name = orig_model_name
        ModelLoader.n_ctx = orig_n_ctx
        tc.CURATED_PATH = orig_curated_path
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_eval_harness_model_and_adapter_selection()
    test_eval_harness_failure_curation()
    print("All eval harness unit tests PASSED!")
