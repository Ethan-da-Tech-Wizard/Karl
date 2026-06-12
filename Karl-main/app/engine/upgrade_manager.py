import os
import json
import subprocess
import requests
from tqdm import tqdm
from core.hardware_scout import get_hardware_profile
from app.engine.model_loader import ModelLoader

REGISTRY_PATH = "data/model_registry.json"
ACTIVE_MODEL_PATH = "data/active_model.json"
MODELS_DIR = "data/models"


def load_registry():
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def load_active_model():
    if os.path.exists(ACTIVE_MODEL_PATH):
        with open(ACTIVE_MODEL_PATH, "r") as f:
            return json.load(f)
    # Default to tier 1 if no active model record exists
    return {"tier": 1, "filename": "deepseek-r1-1.5b.gguf"}


def save_active_model(entry):
    os.makedirs("data", exist_ok=True)
    with open(ACTIVE_MODEL_PATH, "w") as f:
        json.dump({"tier": entry["tier"], "filename": entry["filename"], "name": entry["name"]}, f, indent=2)


def check_for_upgrade():
    """
    Compares current hardware to the registry.
    Returns the highest eligible model entry if it is a higher tier than current,
    otherwise returns None.
    """
    profile = get_hardware_profile()
    registry = load_registry()
    active = load_active_model()

    eligible = [
        e for e in registry
        if profile["ram_gb"] >= e["min_ram_gb"]
        and profile["vram_gb"] >= e["min_vram_gb"]
        and profile["storage_gb"] >= e["min_storage_gb"]
    ]

    if not eligible:
        return None, profile

    best = max(eligible, key=lambda e: e["tier"])

    if best["tier"] > active["tier"]:
        return best, profile

    return None, profile


def download_model(entry, progress_callback=None):
    """Downloads the GGUF file for the given registry entry."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    target = os.path.join(MODELS_DIR, entry["filename"])

    if os.path.exists(target):
        return target

    response = requests.get(entry["url"], stream=True)
    total = int(response.headers.get("content-length", 0))

    with open(target, "wb") as f, tqdm(total=total, unit="iB", unit_scale=True, desc=entry["filename"]) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            size = f.write(chunk)
            bar.update(size)
            if progress_callback:
                progress_callback(bar.n, total)

    return target


def perform_upgrade(entry, progress_callback=None):
    """
    Full upgrade sequence:
    1. Download new GGUF
    2. Reset model singleton
    3. Update active_model.json
    4. Git commit + push
    Returns the new model path.
    """
    model_path = download_model(entry, progress_callback)

    ModelLoader.reset_instance()
    save_active_model(entry)

    _git_record_upgrade(entry)

    return model_path


def _git_record_upgrade(entry):
    """Commits and pushes the upgrade to GitHub."""
    try:
        # Guard: only push if remote is configured
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        if "origin" not in result.stdout:
            return

        commit_msg = f"upgrade(karl): self-upgraded to {entry['name']} (Tier {entry['tier']})"
        subprocess.run(["git", "add", ACTIVE_MODEL_PATH], cwd=os.getcwd())
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=os.getcwd())
        subprocess.run(["git", "push"], cwd=os.getcwd())
    except Exception as e:
        print(f"[UpgradeManager] Git push failed: {e}")
