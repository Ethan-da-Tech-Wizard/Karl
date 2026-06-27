import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.qt_test_helper  # noqa: F401  # Ensures global QApplication runs headlessly
from app.ui.workspaces.system_config.observability_tab import ObservabilityTab

class MockState:
    pass

def test_telemetry_metrics_calculation():
    state = MockState()
    
    # 1. Create a dummy performance telemetry file
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, "performance_telemetry.jsonl")
    
    entries = [
        {
            "ts": "2026-06-27_120000",
            "model": "test-model.gguf",
            "prefill_tokens_count": 100,
            "prefill_duration_sec": 0.5,  # 500 ms TTFT
            "tokens_per_second": 20.0,
            "kv_cache_hits": 20,
            "vram_usage_mb_delta": 10.0
        },
        {
            "ts": "2026-06-27_120100",
            "model": "test-model.gguf",
            "prefill_tokens_count": 200,
            "prefill_duration_sec": 0.3,  # 300 ms TTFT
            "tokens_per_second": 30.0,
            "kv_cache_hits": 100,
            "vram_usage_mb_delta": 20.0
        }
    ]
    
    with open(log_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
            
    import app.ui.workspaces.system_config.observability_tab as ot
    original_path = ot.TELEMETRY_LOG_PATH
    ot.TELEMETRY_LOG_PATH = log_file
    
    tab = ObservabilityTab(state)
    
    try:
        tab.refresh_metrics()
        
        # Verify metric pill values
        # TTFT: (500 + 300) / 2 = 400.0 ms
        assert tab.ttft_pill.val_lbl.text() == "400.0 ms"
        # TPS: (20.0 + 30.0) / 2 = 25.00 t/s
        assert tab.tps_pill.val_lbl.text() == "25.00 t/s"
        # Cache hits: (20 + 100) / (100 + 200) = 120 / 300 = 40.0%
        assert tab.cache_pill.val_lbl.text() == "40.0%"
        # VRAM Delta: (10.0 + 20.0) / 2 = +15.0 MB
        assert tab.vram_pill.val_lbl.text() == "+15.0 MB"
    finally:
        ot.TELEMETRY_LOG_PATH = original_path
        import shutil
        shutil.rmtree(temp_dir)
