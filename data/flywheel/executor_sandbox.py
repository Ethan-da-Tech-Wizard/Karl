import subprocess
import sys
import os
import tempfile
import logging

class SafePythonSandbox:
    """
    Isolated execution environment for running untrusted verifier scripts.
    Prioritizes Docker-based sandboxing with strict resource limits and security guardrails.
    """
    def __init__(self, cpu_timeout_sec: float = 2.0, memory_limit_mb: int = 256):
        self.cpu_timeout_sec = cpu_timeout_sec
        self.memory_limit_mb = memory_limit_mb
        self.image = "python:3.12-slim"

    def _is_docker_available(self) -> bool:
        """Checks if Docker is installed and the daemon is reachable."""
        try:
            # Check if docker command exists and can talk to the daemon
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=5.0
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run_code(self, code: str, test_code: str) -> tuple[bool, str]:
        """
        Executes code + test suite in a restricted environment.
        Returns (passed, stdout/stderr traceback).
        """
        full_script = f"{code}\n\n{test_code}"
        
        if self._is_docker_available():
            return self._run_in_docker(full_script)
        else:
            print("WARNING: Docker unavailable. Falling back to local subprocess sandbox.", file=sys.stderr)
            return self._run_locally(full_script)

    def _run_in_docker(self, script: str) -> tuple[bool, str]:
        """Runs the script inside an ephemeral Docker container."""
        # Security Guardrails:
        # --network none: Disable internet access
        # --memory: Cap RAM usage to prevent OOM on host
        # --cpu-shares: Limit CPU priority
        # --user: Run as non-root user (1000:1000)
        # --rm: Automatically remove container on exit
        cmd = [
            "docker", "run", "--rm", "-i",
            "--network", "none",
            f"--memory={self.memory_limit_mb}m",
            "--cpu-shares=256",
            "--user", "1000:1000",
            self.image,
            "python3"
        ]
        
        try:
            # Script is piped to stdin to avoid volume mounting and permission issues
            proc = subprocess.run(
                cmd,
                input=script,
                capture_output=True,
                text=True,
                timeout=self.cpu_timeout_sec
            )
            
            passed = (proc.returncode == 0)
            output = (proc.stdout + proc.stderr).strip()
            
            if not output and not passed:
                output = f"Container exited with code {proc.returncode}"
                
            return passed, output

        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT: Docker execution exceeded {self.cpu_timeout_sec}s safety budget."
        except Exception as e:
            return False, f"DOCKER EXECUTION ERROR: {e}"

    def _run_locally(self, script: str) -> tuple[bool, str]:
        """Fallback for systems without Docker using local subprocess and resource limits."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(script)
            temp_name = f.name
            
        def set_resource_limits():
            """Applies Unix-specific resource limits to the child process."""
            try:
                import resource
                # Convert MB to Bytes
                mem_limit = self.memory_limit_mb * 1024 * 1024
                # RLIMIT_AS: Max address space
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                # RLIMIT_CPU: Max CPU time in seconds
                cpu_limit = int(self.cpu_timeout_sec) + 1
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
            except (ImportError, ValueError):
                pass

        try:
            # preexec_fn is Unix-only
            proc = subprocess.run(
                [sys.executable, temp_name],
                preexec_fn=set_resource_limits if os.name != 'nt' else None,
                capture_output=True,
                text=True,
                timeout=self.cpu_timeout_sec
            )
            passed = (proc.returncode == 0)
            trace = (proc.stdout + proc.stderr).strip()
            return passed, trace
        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT: Local execution exceeded {self.cpu_timeout_sec}s safety budget."
        except Exception as e:
            return False, f"LOCAL SANDBOX ERROR: {e}"
        finally:
            if os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except OSError:
                    pass
