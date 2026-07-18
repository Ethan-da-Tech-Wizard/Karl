#!/usr/bin/env python3
"""
API & AI Automation SFT Dataset Generator
=========================================
Generates synthetic, high-quality Python instruction-response pairs covering
API client calls (OpenAI, Anthropic), rate-limiting retries, Pydantic parsing,
FastAPI webhooks, and agentic tool-use loops.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("karl.generate_api_automation_sft")

ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "data/training/code/api_automation_sft.jsonl"

# Expert system prompt for coding assistant
SYSTEM_PROMPT = (
    "You are an expert Python software engineer. Prioritise correctness, "
    "idiomatic style, and minimal complexity."
)

# High-quality hand-crafted scenarios for API calls and AI automation
AUTOMATION_SCENARIOS = [
    {
        "instruction": "Write a Python script that calls the OpenAI chat completions API with streaming enabled, using the official openai package.",
        "response": (
            "```python\n"
            "import os\n"
            "from openai import OpenAI\n\n"
            "def stream_openai_response(prompt: str, model: str = 'gpt-4o'):\n"
            "    # Initialize the client. Assumes OPENAI_API_KEY environment variable is set.\n"
            "    client = OpenAI()\n\n"
            "    try:\n"
            "        response = client.chat.completions.create(\n"
            "            model=model,\n"
            "            messages=[{'role': 'user', 'content': prompt}],\n"
            "            stream=True\n"
            "        )\n"
            "        for chunk in response:\n"
            "            content = chunk.choices[0].delta.content\n"
            "            if content:\n"
            "                print(content, end='', flush=True)\n"
            "        print()\n"
            "    except Exception as e:\n"
            "        print(f'Error during streaming generation: {e}')\n"
            "```"
        )
    },
    {
        "instruction": "How do I make an asynchronous HTTP POST request to a REST API in Python using httpx, with custom headers and a json payload?",
        "response": (
            "```python\n"
            "import httpx\n"
            "import asyncio\n"
            "from typing import Any, Dict\n\n"
            "async def send_post_request(url: str, payload: Dict[str, Any], token: str) -> Dict[str, Any]:\n"
            "    headers = {\n"
            "        'Authorization': f'Bearer {token}',\n"
            "        'Content-Type': 'application/json'\n"
            "    }\n"
            "    async with httpx.AsyncClient() as client:\n"
            "        response = await client.post(url, json=payload, headers=headers, timeout=10.0)\n"
            "        response.raise_for_status()\n"
            "        return response.json()\n"
            "```"
        )
    },
    {
        "instruction": "Implement a Python function that uses the tenacity library to retry an API call with exponential backoff if it raises rate limit or connection errors.",
        "response": (
            "```python\n"
            "import httpx\n"
            "from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type\n\n"
            "# Retry on connection errors or HTTP status code exceptions\n"
            "@retry(\n"
            "    stop=stop_after_attempt(5),\n"
            "    wait=wait_exponential(multiplier=1, min=2, max=10),\n"
            "    retry=retry_if_exception_type((httpx.ConnectError, httpx.HTTPStatusError)),\n"
            "    reraise=True\n"
            ")\n"
            "def fetch_data_with_retry(url: str) -> dict:\n"
            "    response = httpx.get(url, timeout=5.0)\n"
            "    response.raise_for_status()\n"
            "    return response.json()\n"
            "```"
        )
    },
    {
        "instruction": "Define a Pydantic v2 schema for parsing a structured AI agent's plan containing tasks, each task having a title, deadline, status, and list of sub-steps.",
        "response": (
            "```python\n"
            "from typing import List, Literal\n"
            "from pydantic import BaseModel, Field\n\n"
            "class SubStep(BaseModel):\n"
            "    description: str = Field(description='Detailed action instruction.')\n"
            "    completed: bool = Field(default=False)\n\n"
            "class Task(BaseModel):\n"
            "    title: str = Field(description='Short name of the task.')\n"
            "    deadline: str = Field(description='Target completion date in YYYY-MM-DD.')\n"
            "    status: Literal['pending', 'in_progress', 'completed'] = 'pending'\n"
            "    steps: List[SubStep] = Field(default_factory=list)\n\n"
            "class AgentPlan(BaseModel):\n"
            "    objective: str = Field(description='High-level goal description.')\n"
            "    tasks: List[Task] = Field(description='Decomposed tasks to achieve the goal.')\n"
            "```"
        )
    },
    {
        "instruction": "Write a FastAPI webhook receiver endpoint in Python that validates a cryptographic signature header using HMAC-SHA256 before processing the payload.",
        "response": (
            "```python\n"
            "import hmac\n"
            "import hashlib\n"
            "from fastapi import FastAPI, Request, HTTPException, Header\n\n"
            "app = FastAPI()\n"
            "WEBHOOK_SECRET = b'super_secret_signing_key'\n\n"
            "async def verify_signature(request: Request, x_signature: str):\n"
            "    body = await request.body()\n"
            "    expected = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()\n"
            "    if not hmac.compare_digest(expected, x_signature):\n"
            "        raise HTTPException(status_code=401, detail='Invalid signature header.')\n\n"
            "@app.post('/webhooks/stripe')\n"
            "async def stripe_webhook(request: Request, x_signature: str = Header(...)):\n"
            "    await verify_signature(request, x_signature)\n"
            "    payload = await request.json()\n"
            "    # Process webhook events\n"
            "    return {'status': 'processed'}\n"
            "```"
        )
    },
    {
        "instruction": "Create an agentic execution loop that calls custom Python tools. It must parse the model's function-calling output and execute the corresponding function.",
        "response": (
            "```python\n"
            "import json\n"
            "from typing import Callable, Dict, Any\n\n"
            "# Define mock tools\n"
            "def calculate_sum(a: int, b: int) -> str:\n"
            "    return str(a + b)\n\n"
            "TOOL_REGISTRY: Dict[str, Callable] = {\n"
            "    'calculate_sum': calculate_sum\n"
            "}\n\n"
            "def execute_tool_call(tool_name: str, arguments_json: str) -> str:\n"
            "    if tool_name not in TOOL_REGISTRY:\n"
            "        return f'Error: Tool {tool_name} not registered.'\n"
            "    try:\n"
            "        args = json.loads(arguments_json)\n"
            "        result = TOOL_REGISTRY[tool_name](**args)\n"
            "        return result\n"
            "    except Exception as e:\n"
            "        return f'Execution failed: {e}'\n"
            "```"
        )
    },
    {
        "instruction": "Write a Python function using the huggingface_hub library to upload a directory of local GGUF models or LoRA adapters to a Hugging Face repository.",
        "response": (
            "```python\n"
            "from huggingface_hub import HfApi\n\n"
            "def upload_adapter_to_hf(local_dir: str, repo_id: str, token: str):\n"
            "    api = HfApi()\n"
            "    api.create_repo(repo_id=repo_id, token=token, repo_type='model', exist_ok=True)\n"
            "    api.upload_folder(\n"
            "        folder_path=local_dir,\n"
            "        repo_id=repo_id,\n"
            "        repo_type='model',\n"
            "        token=token,\n"
            "        commit_message='Upload fine-tuned LoRA adapter from Karl Studio'\n"
            "    )\n"
            "    print(f'Successfully uploaded adapter directory {local_dir} to {repo_id}')\n"
            "```"
        )
    }
]


def main() -> int:
    logger.info("Generating API and AI automation synthetic SFT examples...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    written = 0
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for scenario in AUTOMATION_SCENARIOS:
            sft_entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": scenario["instruction"]},
                    {"role": "assistant", "content": scenario["response"]}
                ],
                "source": "api_automation_synthetic"
            }
            fh.write(json.dumps(sft_entry, ensure_ascii=False) + "\n")
            written += 1
            
    logger.info("Successfully wrote %d automation examples to %s", written, OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
