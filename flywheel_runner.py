import os
import time
import json
import uuid
import logging
import threading
from typing import Optional

from app.engine.model_loader import ModelLoader
from app.engine import config_store
from core.cognitive_parser import parse_thought_stream

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("karl.flywheel_runner")

QUEUE_DIR = os.path.join("data", "flywheel", "queue")
EXECUTION_DIR = os.path.join("data", "flywheel", "execution")

def write_json_atomic(path: str, data: dict):
    """Write JSON data to a path atomically."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, path)

def process_task(task_path: str, llm):
    task_id_file = os.path.basename(task_path)
    logger.info("Processing task: %s", task_id_file)
    
    try:
        with open(task_path, "r", encoding="utf-8") as f:
            task = json.load(f)
    except Exception as e:
        logger.error("Failed to load task %s: %s", task_id_file, e)
        # Move to a failed directory or just delete? For now, just delete to keep queue clear
        os.remove(task_path)
        return

    problem = task.get("problem_statement", "")
    if not problem:
        logger.warning("Task %s has no problem_statement", task_id_file)
        os.remove(task_path)
        return

    try:
        # Wrap query in DeepSeek-R1 prompt structure
        # User prompt + Assistant pre-seed
        prompt = f"User: {problem}\nAssistant: <think>\n"
        
        logger.info("Executing LLM for task %s", task_id_file)
        
        # We want to capture the thinking and the output.
        # Since we pre-seeded <think>, we expect the model to finish the thinking block and then give the answer.
        output_chunks = []
        for chunk in llm(
            prompt,
            max_tokens=task.get("max_tokens", 4096),
            stop=["User:", "<think>"], # Safety stops
            stream=True
        ):
            text = chunk["choices"][0]["text"]
            output_chunks.append(text)
            
        full_output = "".join(output_chunks)
        thought, response = parse_thought_stream(full_output)
        
        # Prepare execution log
        exec_id = str(uuid.uuid4())
        exec_log = {
            "id": exec_id,
            "task_id": task.get("id", "unknown"),
            "problem_statement": problem,
            "ground_truth_answer": task.get("ground_truth_answer", ""),
            "verification_type": task.get("verification_type", ""),
            "verification_script": task.get("verification_script", ""),
            "model_thought": thought,
            "model_response": response
        }
        
        exec_filename = f"exec_{exec_id}.json"
        exec_path = os.path.join(EXECUTION_DIR, exec_filename)
        
        write_json_atomic(exec_path, exec_log)
        logger.info("Execution log written: %s", exec_filename)
        
        # Delete task from queue
        os.remove(task_path)
        logger.info("Task %s removed from queue", task_id_file)
        
    except Exception as e:
        logger.error("Error processing task %s: %s", task_id_file, e, exc_info=True)

def main():
    logger.info("Flywheel Runner (Agent 2) started. Watching %s", QUEUE_DIR)
    
    llm = None
    
    while True:
        try:
            files = [f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")]
            if not files:
                time.sleep(1)
                continue
            
            # Ensure model is loaded once
            if llm is None:
                logger.info("Initializing ModelLoader instance...")
                llm = ModelLoader.get_instance()
            
            # Process one task at a time
            files.sort() # Process in some order
            process_task(os.path.join(QUEUE_DIR, files[0]), llm)
            
        except Exception as e:
            logger.error("Main loop error: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
