#!/usr/bin/env bash
# setup_gpu.sh — Script to configure NVIDIA GPU, compile DKMS, reinstall CUDA PyTorch, and verify CUDA.

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Karl GPU & PyTorch Setup Script ===${NC}"

# 1. Check if running with sudo/root permissions for system installs
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Warning: This script needs root privileges to install packages and load kernel modules.${NC}"
    echo -e "${YELLOW}    Please run: sudo ./setup_gpu.sh${NC}"
    exit 1
fi

# Get the original user (who invoked sudo) to locate venv correctly
ORIGINAL_USER=${SUDO_USER:-$USER}
ORIGINAL_HOME=$(getent passwd "$ORIGINAL_USER" | cut -d: -f6)
PROJECT_DIR="$(pwd)"

echo -e "${BLUE}[*] Detected user: $ORIGINAL_USER (Home: $ORIGINAL_HOME)${NC}"
echo -e "${BLUE}[*] Project directory: $PROJECT_DIR${NC}"

# 2. Check and install linux-headers
RUNNING_KERNEL=$(uname -r)
echo -e "${BLUE}[*] Current running kernel: $RUNNING_KERNEL${NC}"

if pacman -Qi linux-headers &>/dev/null; then
    echo -e "${GREEN}[✓] linux-headers is already installed.${NC}"
else
    echo -e "${YELLOW}[*] linux-headers is missing. Installing...${NC}"
    pacman -S --noconfirm linux-headers
    echo -e "${GREEN}[✓] linux-headers installed.${NC}"
fi

# 3. Compile and Load NVIDIA modules
echo -e "${BLUE}[*] Registering/Building DKMS modules...${NC}"
dkms autoinstall || echo -e "${YELLOW}[!] DKMS autoinstall returned non-zero. Modules might already be built.${NC}"

echo -e "${BLUE}[*] Checking if NVIDIA modules are loaded...${NC}"
if ! lsmod | grep -q "^nvidia"; then
    echo -e "${YELLOW}[*] NVIDIA modules not loaded. Attempting to load...${NC}"
    modprobe nvidia
    modprobe nvidia-uvm
    modprobe nvidia-drm
    echo -e "${GREEN}[✓] NVIDIA modules loaded.${NC}"
else
    echo -e "${GREEN}[✓] NVIDIA modules are already loaded.${NC}"
fi

# Verify nvidia-smi works
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
    echo -e "${GREEN}[✓] nvidia-smi is working! GPU is active.${NC}"
else
    echo -e "${RED}[✗] nvidia-smi failed. The driver could not communicate with the GPU.${NC}"
    echo -e "${RED}    Please ensure you have switched your graphics manager to Hybrid/NVIDIA mode and rebooted.${NC}"
    exit 1
fi

# 4. Reinstall PyTorch and training tools in the project venv
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}[✗] Virtual environment not found at $VENV_DIR.${NC}"
    echo -e "${RED}    Please run this script from the root of the Karl repository.${NC}"
    exit 1
fi

echo -e "${BLUE}[*] Upgrading pip and installing CUDA-enabled PyTorch in virtual environment...${NC}"
# Run as the original user to avoid permission issues in the venv folder
sudo -u "$ORIGINAL_USER" "$VENV_DIR/bin/pip" install --upgrade pip

echo -e "${BLUE}[*] Installing PyTorch with CUDA 12.1...${NC}"
sudo -u "$ORIGINAL_USER" "$VENV_DIR/bin/pip" install torch --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

echo -e "${BLUE}[*] Installing HuggingFace training dependencies (transformers, peft, trl, datasets, bitsandbytes, accelerate)...${NC}"
sudo -u "$ORIGINAL_USER" "$VENV_DIR/bin/pip" install transformers peft trl datasets bitsandbytes accelerate gguf

# 5. Verify CUDA is active in PyTorch
echo -e "${BLUE}[*] Verifying CUDA support in PyTorch virtual environment...${NC}"
CUDA_VERIFY=$(sudo -u "$ORIGINAL_USER" "$VENV_DIR/bin/python" -c "
import torch
available = torch.cuda.is_available()
count = torch.cuda.device_count() if available else 0
name = torch.cuda.get_device_name(0) if available else 'N/A'
print(f'STATUS:{available}:{count}:{name}')
")

# Parse verification output
IFS=':' read -r _ AVAILABLE COUNT NAME <<< "$CUDA_VERIFY"

if [ "$AVAILABLE" == "True" ]; then
    echo -e "${GREEN}[✓] SUCCESS: PyTorch detects GPU acceleration!${NC}"
    echo -e "${GREEN}    Device count: $COUNT${NC}"
    echo -e "${GREEN}    Primary GPU:  $NAME${NC}"
    echo -e "${GREEN}=== Setup Complete! You are ready to train LoRA models in Karl ===${NC}"
else
    echo -e "${RED}[✗] ERROR: PyTorch was installed but does not detect the GPU.${NC}"
    echo -e "${RED}    (torch.cuda.is_available() returned False)${NC}"
    exit 1
fi
