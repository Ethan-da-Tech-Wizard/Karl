import subprocess
import sys
import os
import shutil
import tempfile
import logging

logger = logging.getLogger("karl.sandbox")


class SafePythonSandbox:
    """
    Isolated execution environment for running untrusted verifier scripts.
    Prioritizes Docker-based sandboxing with strict resource limits and security guardrails.

    Falls back to a bubblewrap (bwrap) namespace jail when Docker is unavailable.
    If neither Docker nor bwrap are present, execution is refused outright —
    this class must never run untrusted/LLM-generated code as a bare host
    subprocess with only rlimits, since rlimits alone give no filesystem or
    network isolation.
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
        # --pids-limit: Bound the number of processes/threads (fork-bomb protection)
        # --read-only: Immutable root filesystem inside the container
        # --security-opt no-new-privileges: Block setuid/setgid privilege escalation
        # --cap-drop ALL: Strip every Linux capability the container doesn't need
        # --user: Run as non-root user (1000:1000)
        # --rm: Automatically remove container on exit
        cmd = [
            "docker", "run", "--rm", "-i",
            "--network", "none",
            f"--memory={self.memory_limit_mb}m",
            "--cpu-shares=256",
            "--pids-limit=64",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
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

    def _build_bwrap_cmd(self, bwrap_path: str, temp_name: str) -> list[str]:
        """
        Build a bubblewrap invocation that runs the interpreter in its own
        mount/network/PID namespace.

        The host root is bound read-only rather than cherry-picking specific
        system/interpreter directories: this host's actual layout (a uv-managed
        CPython install symlinked in from outside /usr, reached through a venv
        under the project directory) showed that selectively binding "/usr",
        "/lib", etc. is fragile and can leave the interpreter's own
        entrypoint unresolvable inside the sandbox depending on how Python
        was installed — silently turning "hardened" into "broken" is worse
        than being conservative here. A whole-root read-only bind resolves
        any interpreter layout uniformly.

        This still closes the two critical gaps from the unsandboxed
        fallback: nothing can be written outside the ephemeral, private
        /tmp (the root bind is read-only and /proc, /dev, /tmp are
        overlaid fresh), and nothing can reach the network at all
        (--unshare-net) — so even though the sandboxed script can still
        *read* arbitrary host files (e.g. bridge_token.json), it has no
        way to exfiltrate them or persist anything outside this process's
        lifetime. Host process visibility is also hidden (--unshare-pid).
        """
        cmd = [
            bwrap_path,
            "--ro-bind", "/", "/",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--ro-bind", temp_name, temp_name,
            "--unshare-net",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-ipc",
            "--die-with-parent",
            "--new-session",
            "--chdir", "/tmp",
            sys.executable, temp_name,
        ]
        return cmd

    def _run_locally(self, script: str) -> tuple[bool, str]:
        """
        Fallback for systems without Docker. Requires bubblewrap (bwrap) to
        provide real filesystem/network/PID isolation — rlimits alone (memory
        and CPU time) bound resource usage but grant no containment, so
        running untrusted/LLM-generated code with only rlimits is refused
        outright rather than silently downgrading to an unsandboxed
        subprocess.
        """
        bwrap_path = shutil.which("bwrap")
        if not bwrap_path:
            logger.error(
                "Sandbox unavailable: neither Docker nor bubblewrap (bwrap) "
                "found on this host. Refusing to execute untrusted code."
            )
            return False, (
                "SANDBOX UNAVAILABLE: neither Docker nor bubblewrap (bwrap) are "
                "installed. Install one of them to run verifier code — refusing "
                "to fall back to an unsandboxed subprocess."
            )

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(script)
            temp_name = f.name

        def set_resource_limits():
            """Applies Unix-specific resource limits to the child process.

            preexec_fn runs after fork() but before bwrap's own exec(), so
            these rlimits are inherited across bwrap's exec into the
            sandboxed interpreter — defense in depth alongside the namespace
            isolation bwrap itself provides.
            """
            try:
                import resource
                # Convert MB to Bytes
                mem_limit = self.memory_limit_mb * 1024 * 1024
                # RLIMIT_AS: Max address space
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                # RLIMIT_CPU: Max CPU time in seconds
                cpu_limit = int(self.cpu_timeout_sec) + 1
                resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
                # Note: RLIMIT_NPROC is deliberately not set here — it is a
                # per-real-UID limit (not scoped to this subtree), so a low
                # absolute value breaks immediately on any host where the
                # invoking user already has more processes than that running
                # elsewhere. Fork-bomb containment instead comes from bwrap's
                # --unshare-pid + --die-with-parent below, which kills the
                # entire sandboxed process tree when the namespace's init
                # process (or the timeout) exits.
            except (ImportError, ValueError):
                pass

        try:
            cmd = self._build_bwrap_cmd(bwrap_path, temp_name)
            # preexec_fn is Unix-only
            proc = subprocess.run(
                cmd,
                preexec_fn=set_resource_limits if os.name != 'nt' else None,
                capture_output=True,
                text=True,
                timeout=self.cpu_timeout_sec,
                env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
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
