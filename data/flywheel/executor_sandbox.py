import subprocess
import sys
import os
import resource
import tempfile

class SafePythonSandbox:
    def __init__(self, cpu_timeout_sec: float = 2.0, memory_limit_mb: int = 128):
        self.cpu_timeout_sec = cpu_timeout_sec
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024

    def _set_resource_limits(self):
        # Set memory limit (address space)
        resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit_bytes, self.memory_limit_bytes))
        # Set CPU execution limit
        resource.setrlimit(resource.RLIMIT_CPU, (int(self.cpu_timeout_sec) + 1, int(self.cpu_timeout_sec) + 1))

    def run_code(self, code: str, test_code: str) -> tuple[bool, str]:
        """
        Executes code + test suite in a restricted subprocess.
        Returns (passed, stdout/stderr traceback).
        """
        full_script = f"{code}\n\n{test_code}"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(full_script)
            temp_name = f.name
        try:
            proc = subprocess.run(
                [sys.executable, temp_name],
                preexec_fn=self._set_resource_limits,
                capture_output=True,
                text=True,
                timeout=self.cpu_timeout_sec
            )
            passed = (proc.returncode == 0)
            trace = (proc.stdout + proc.stderr).strip()
            return passed, trace
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT: Execution exceeded safety budget."
        except Exception as e:
            return False, f"SANDBOX ERROR: {e}"
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)
