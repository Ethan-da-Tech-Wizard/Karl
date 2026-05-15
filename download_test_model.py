import os
import requests
from tqdm import tqdm

def download_file(url, filepath):
    # Streaming download with progress bar
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 # 1 Kibibyte
    
    with open(filepath, 'wb') as file, tqdm(
        desc=os.path.basename(filepath),
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)

if __name__ == "__main__":
    # Downloads DeepSeek-R1-Distill-Qwen-1.5B (Q4_K_M quantized, ~986 MB).
    # This is the default Tier-1 model for Karl — see data/model_registry.json.
    url = "https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
    
    os.makedirs("data/models", exist_ok=True)
    target_path = "data/models/deepseek-r1-1.5b.gguf"
    
    if not os.path.exists(target_path):
        print(f"Downloading test model to {target_path}...")
        download_file(url, target_path)
        print("Download complete!")
    else:
        print(f"Model already exists at {target_path}")
