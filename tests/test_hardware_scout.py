import io
import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hardware_scout import get_hardware_profile, get_hardware_uuid
from tests.conftest import requires_gputil


def test_hardware_profile_structure():
    """Verify structure, types, and values in the hardware profile output."""
    profile = get_hardware_profile()
    
    assert isinstance(profile, dict)
    assert "ram_gb" in profile
    assert "vram_gb" in profile
    assert "storage_gb" in profile
    
    assert isinstance(profile["ram_gb"], float)
    assert isinstance(profile["vram_gb"], float)
    assert isinstance(profile["storage_gb"], float)
    
    assert profile["ram_gb"] >= 0.0
    assert profile["vram_gb"] >= 0.0
    assert profile["storage_gb"] >= 0.0


@requires_gputil
def test_hardware_profile_gpu_mocking():
    """Verify VRAM scanning behavior when GPUtil returns mock GPU specs."""
    class DummyGPU:
        def __init__(self, memory_free):
            self.memoryFree = memory_free
            
    # Mock GPUtil.getGPUs to return custom mock GPUs
    with mock.patch("GPUtil.getGPUs") as mock_get_gpus:
        mock_get_gpus.return_value = [DummyGPU(4096.0), DummyGPU(8192.0)]
        profile = get_hardware_profile()
        # VRAM is max of free memory on GPUs divided by 1024 (8192 / 1024 = 8.0)
        assert profile["vram_gb"] == 8.0


@requires_gputil
def test_hardware_profile_gpu_exception_fallback():
    """Verify clean fallback to 0.0 GB VRAM when GPUtil throws an error."""
    with mock.patch("GPUtil.getGPUs") as mock_get_gpus:
        mock_get_gpus.side_effect = Exception("CUDA driver not loaded")
        profile = get_hardware_profile()
        assert profile["vram_gb"] == 0.0


def test_hardware_uuid_permission_error_falls_through_to_next_path():
    """A PermissionError on one DMI path (e.g. product_uuid is root-only,
    mode 0400, on many distros) must not abort the whole loop -- it should
    still try the remaining paths (/etc/machine-id) instead of silently
    falling through to the non-deterministic uuid.getnode() fallback,
    which would change the derived trace-archive encryption key on every
    restart. Regression test for that exact failure mode."""

    def fake_exists(path):
        return path in (
            "/sys/class/dmi/id/product_uuid",
            "/etc/machine-id",
        )

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/sys/class/dmi/id/product_uuid":
            raise PermissionError(f"[Errno 13] Permission denied: '{path}'")
        if path == "/etc/machine-id":
            return io.StringIO("stable-machine-id-value\n")
        raise FileNotFoundError(path)

    with mock.patch("platform.system", return_value="Linux"), \
         mock.patch("os.path.exists", side_effect=fake_exists), \
         mock.patch("builtins.open", side_effect=fake_open):
        assert get_hardware_uuid() == "stable-machine-id-value"


def test_hardware_uuid_stable_across_calls():
    """The real (unmocked) UUID must be identical across repeated calls --
    it's used as a key-derivation salt, so any instability here would make
    previously-encrypted trace archives undecryptable."""
    assert get_hardware_uuid() == get_hardware_uuid()
