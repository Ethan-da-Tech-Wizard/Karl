import os
import shutil
import platform
import subprocess

def get_cpu_flags() -> list[str]:
    """Returns a list of CPU instruction flags (avx, avx2, etc.)."""
    flags = []
    try:
        system = platform.system()
        if system == "Linux":
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("flags") or line.startswith("Features"):
                            content = line.lower()
                            # Check for common vector extensions
                            candidates = ["avx", "avx2", "avx512f", "fma", "sse4_1", "sse4_2", "neon"]
                            for cand in candidates:
                                if f" {cand} " in content or f"\t{cand} " in content or content.endswith(f" {cand}\n"):
                                    flags.append(cand)
        elif system == "Darwin":
            # macOS uses sysctl
            result = subprocess.run(["sysctl", "-a"], capture_output=True, text=True)
            content = result.stdout.lower()
            candidates = {
                "hw.optional.avx1_0": "avx",
                "hw.optional.avx2_0": "avx2",
                "hw.optional.avx512f": "avx512f",
                "hw.optional.fma": "fma",
                "hw.optional.neon": "neon",
                "hw.optional.armv8_crc32": "crc32"
            }
            for key, val in candidates.items():
                if f"{key}: 1" in content:
                    flags.append(val)
    except Exception:
        pass
    return sorted(list(set(flags)))

def get_hardware_uuid() -> str:
    """Retrieves physical motherboard UUID or a stable hardware-bound fallback."""
    system = platform.system()
    try:
        if system == "Linux":
            # Prefer non-root DMI paths
            for path in [
                "/sys/class/dmi/id/product_uuid",
                "/sys/devices/virtual/dmi/id/product_uuid",
                "/etc/machine-id"
            ]:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        uuid_str = f.read().strip()
                        if uuid_str: return uuid_str
        elif system == "Darwin":
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            # Example output: "IOPlatformUUID" = "5B1E...B0D"
            if "IOPlatformUUID" in result.stdout:
                return result.stdout.split("=")[-1].replace('"', '').strip()
    except Exception:
        pass

    # Fallback: Hash MAC addresses + CPU Info
    try:
        import uuid
        import hashlib
        mac = str(uuid.getnode())
        cpu = platform.processor()
        seed = f"{mac}-{cpu}-{system}"
        return hashlib.sha256(seed.encode()).hexdigest()
    except Exception:
        return "karl-static-hardware-fallback"

def get_hardware_profile():
    """
    Returns a dict of available hardware resources including CPU flags.
    GPUtil is optional — if no discrete GPU is found, vram_gb = 0.0.
    """
    import psutil

    ram_gb = psutil.virtual_memory().available / (1024 ** 3)

    vram_gb = 0.0
    gpu_list: list[dict] = []
    
    # ── NVIDIA NVML Monitoring ───────────────────────────────────────────────
    nvml_info = {}
    try:
        import pynvml
        pynvml.nvmlInit()
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # Fetch Temperature
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Fetch Throttle Reasons
                reasons = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
                alerts = []
                if reasons & pynvml.NVML_CLOCKS_THROTTLE_REASON_THERMAL:
                    alerts.append("Thermal Throttling Active")
                if reasons & pynvml.NVML_CLOCKS_THROTTLE_REASON_POWER_LIMIT:
                    alerts.append("Power Limit Throttling Active")
                
                nvml_info[i] = {
                    "temp_c": temp,
                    "alerts": alerts
                }
        finally:
            pynvml.nvmlShutdown()
    except Exception:
        pass # NVML not available or no NVIDIA GPU
    # ─────────────────────────────────────────────────────────────────────────

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            vram_gb = max(gpu.memoryFree / 1024 for gpu in gpus)
            for gpu in gpus:
                gpu_data = {
                    "id": gpu.id,
                    "name": gpu.name,
                    "memory_free_mb": gpu.memoryFree,
                    "memory_total_mb": gpu.memoryTotal,
                }
                # Inject NVML data if available for this ID
                if gpu.id in nvml_info:
                    gpu_data["temperature_c"] = nvml_info[gpu.id]["temp_c"]
                    gpu_data["alerts"] = nvml_info[gpu.id]["alerts"]
                
                gpu_list.append(gpu_data)
    except Exception:
        pass  # No discrete GPU or GPUtil not available

    # Storage free on the drive where Karl lives
    karl_dir = os.path.dirname(os.path.abspath(__file__))
    total, used, free = shutil.disk_usage(karl_dir)
    storage_gb = free / (1024 ** 3)

    # Calculate max temperature if available
    max_temp = None
    temps = [g.get("temperature_c") for g in gpu_list if g.get("temperature_c") is not None]
    if temps:
        max_temp = max(temps)

    return {
        "ram_gb": round(ram_gb, 2),
        "vram_gb": round(vram_gb, 2),
        "storage_gb": round(storage_gb, 2),
        "gpu_temp_c": max_temp,
        "hardware_uuid": get_hardware_uuid(),
        "cpu_flags": get_cpu_flags(),
        "arch": platform.machine(),
        "os": platform.system(),
        "gpu_list": gpu_list,
    }


if __name__ == "__main__":
    profile = get_hardware_profile()
    print(f"RAM available:     {profile['ram_gb']:.1f} GB")
    print(f"VRAM available:    {profile['vram_gb']:.1f} GB")
    print(f"Storage available: {profile['storage_gb']:.1f} GB")
