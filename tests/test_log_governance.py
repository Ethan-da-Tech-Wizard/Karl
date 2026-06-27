import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.trace_logger import TraceLogger

def test_log_retention_policy_enforcement():
    # 1. Create a temporary folder for mock logs
    temp_dir = tempfile.mkdtemp()
    
    # 2. Instantiate TraceLogger pointing to this temp dir
    logger_inst = TraceLogger(log_dir=temp_dir, archive_dir=os.path.join(temp_dir, "archive"))
    
    # Create 3 very old files (age = 15 days)
    old_files = []
    for i in range(3):
        fn = f"trace_old_{i}.jsonl"
        path = os.path.join(temp_dir, fn)
        with open(path, "w") as f:
            f.write("A" * 1024)  # 1 KB
        # Set mtime back 15 days
        past_time = time.time() - (15 * 24 * 3600)
        os.utime(path, (past_time, past_time))
        old_files.append(path)
        
    # Create 4 newer but large files, offset mtimes slightly so they have a sorting order
    new_files = []
    for i in range(4):
        fn = f"trace_new_{i}.jsonl"
        path = os.path.join(temp_dir, fn)
        with open(path, "w") as f:
            f.write("B" * 50 * 1024)  # 50 KB each -> 200 KB total
        # Offset mtime by i minutes to guarantee order
        time_offset = time.time() + (i * 60)
        os.utime(path, (time_offset, time_offset))
        new_files.append(path)
        
    try:
        from app.engine import config_store
        original_get_config = config_store.get_ui_config
        
        config_store.get_ui_config = lambda: {
            "log_retention_days": 5,
            "max_log_disk_size_mb": 100 / 1024  # 100 KB limit
        }
        
        # Enforce retention policy
        logger_inst.enforce_retention_policy(logs_dir=temp_dir)
        
        # 1. Old files (15 days old) MUST be deleted due to age sweep
        for path in old_files:
            assert not os.path.exists(path)
            
        # 2. Total size of newer files was 200 KB, but our limit is 100 KB
        # Oldest files in the quota subset should be deleted until size <= 100 KB
        remaining_new = [p for p in new_files if os.path.exists(p)]
        assert len(remaining_new) == 2
        
        # Total size must be <= 100 KB
        total_remaining_size = sum(os.path.getsize(p) for p in remaining_new)
        assert total_remaining_size <= 100 * 1024
        
    finally:
        config_store.get_ui_config = original_get_config
        import shutil
        shutil.rmtree(temp_dir)
