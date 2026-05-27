import os
import shutil

def get_hardware_profile():
    """
    Returns a dict of available hardware resources.
    GPUtil is optional — if no discrete GPU is found, vram_gb = 0.0.
    """
    import psutil

    ram_gb = psutil.virtual_memory().total / (1024 ** 3)

    vram_gb = 0.0
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            vram_gb = max(gpu.memoryFree / 1024 for gpu in gpus)
    except Exception:
        pass  # No discrete GPU or GPUtil not available

    # Storage free on the drive where Karl lives
    karl_dir = os.path.dirname(os.path.abspath(__file__))
    total, used, free = shutil.disk_usage(karl_dir)
    storage_gb = free / (1024 ** 3)

    return {
        "ram_gb": round(ram_gb, 2),
        "vram_gb": round(vram_gb, 2),
        "storage_gb": round(storage_gb, 2)
    }


if __name__ == "__main__":
    profile = get_hardware_profile()
    print(f"RAM available:     {profile['ram_gb']:.1f} GB")
    print(f"VRAM available:    {profile['vram_gb']:.1f} GB")
    print(f"Storage available: {profile['storage_gb']:.1f} GB")
