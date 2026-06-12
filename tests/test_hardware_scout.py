import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hardware_scout import get_hardware_profile
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
