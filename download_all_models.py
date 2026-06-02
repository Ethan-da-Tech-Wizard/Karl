import os
import argparse
import json
import requests
from tqdm import tqdm

def download_file(url, filepath):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1 MB block size
    
    with open(filepath, 'wb') as file, tqdm(
        desc=os.path.basename(filepath),
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(block_size):
            if data:
                size = file.write(data)
                bar.update(size)

def main():
    parser = argparse.ArgumentParser(description="Download Karl LLM models from the registry.")
    parser.add_argument(
        "--tier", type=int, choices=[1, 2, 3, 4], help="Download all models of a specific tier (e.g. tier 2 for 7B/8B class models)."
    )
    parser.add_argument(
        "--all", action="store_true", help="Download all models in the registry."
    )
    args = parser.parse_args()

    registry_path = "data/model_registry.json"
    if not os.path.exists(registry_path):
        print(f"Registry not found at {registry_path}")
        return

    with open(registry_path, "r") as f:
        registry = json.load(f)

    os.makedirs("data/models", exist_ok=True)

    to_download = []
    if args.all:
        to_download = registry
    elif args.tier is not None:
        to_download = [m for m in registry if m.get("tier") == args.tier]
    else:
        # Interactive selection
        print("Available models in registry:")
        for idx, m in enumerate(registry, 1):
            file_path = os.path.join("data/models", m["filename"])
            status = "[Downloaded]" if os.path.exists(file_path) else "[Not Downloaded]"
            print(f"  {idx}. Tier {m['tier']}: {m['name']} ({m['min_storage_gb']} GB) {status}")
        
        try:
            choice = input("\nEnter numbers of models to download (comma separated, e.g. 2,3), or 'all': ").strip().lower()
            if choice == 'all':
                to_download = registry
            else:
                indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
                to_download = [registry[i] for i in indices if 0 <= i < len(registry)]
        except (KeyboardInterrupt, SystemExit):
            print("\nCancelled.")
            return
        except Exception:
            print("Invalid input.")
            return

    if not to_download:
        print("No models selected for download.")
        return

    for m in to_download:
        target = os.path.join("data/models", m["filename"])
        print(f"\nProcessing {m['name']}...")
        if os.path.exists(target):
            print(f"Model already exists at {target}")
            continue
        
        print(f"Downloading from: {m['url']}")
        try:
            download_file(m["url"], target)
            print(f"Successfully downloaded to {target}")
        except Exception as e:
            print(f"Error downloading {m['name']}: {e}")

if __name__ == "__main__":
    main()
