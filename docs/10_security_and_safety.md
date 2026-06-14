# Security and Safety Guide

Karl is designed as a **privacy-first, offline-only** instrument. However, because it has the power to execute code, ingest files, and interact with your local environment via a WebSocket bridge, it is important to understand the security model and follow best practices.

---

## 1. The Security Model

### Zero-Remote Invariants
- **No Telemetry:** Karl does not send usage statistics, crash reports, or prompts to any remote server.
- **Local Inference:** All model weights (GGUF) are executed locally on your CPU/GPU.
- **Offline RAG:** Your Knowledge Base (FAISS index) and traces are stored locally in `data/`.

### The Bridge (WebSocket)
Karl hosts a WebSocket server on `localhost:8080` (configurable). This is the "control surface" for the VS Code extension.
- **Risk:** Any local application or a malicious website (via Cross-Site WebSocket Hijacking) could theoretically connect to this port if Karl is running and no authentication is present.
- **Current Guardrails:** Karl currently restricts connections to `localhost`. We are moving toward a token-based authentication system for the bridge.

### The Agentic Swarm
The Swarm Orchestrator can plan, write, and test code.
- **Risk:** If given a malicious objective or a dangerous `test_command`, an agent could delete files or execute harmful shell commands.
- **Guardrail:** All file edits proposed by agents are shown as **Visible Diffs** in the editor. You must explicitly "Accept" these changes.
- **Guardrail:** The `SwarmOrchestrator` uses a transaction-based approach with `.original` backups.

---

## 2. Best Practices for Safe Usage

### Trust Your Workspace
Only run Karl (and especially the Agent Swarm) against directories you trust. Avoid running Karl as root or with administrative privileges.

### Review Agent Plans
Before clicking "Accept" on a swarm-generated change, review the code. Agents are powerful but can be hallucinated into creating security vulnerabilities or bugs.

### Sensitive Data in Knowledge Base
Karl's Knowledge Base stores extracted text in a local `metadata.json` and a FAISS index. These files are **unencrypted**. If you ingest sensitive credentials or private documents, ensure your machine's filesystem is encrypted (e.g., LUKS or FileVault).

### Bridge Management
If you are not using the VS Code extension, you can disable the WebSocket bridge in the **System Config** workspace to reduce your local attack surface.

---

## 3. Responsible AI & Privacy

### Respect Others' Privacy
When using Karl to analyze datasets or communications, remember to respect the privacy of the individuals involved. Do not use Karl to process stolen data or perform unauthorized surveillance.

### No "Hacker AI"
Karl is an **introspection tool** for builders. Do not attempt to use the agentic loops to create "autonomous hackers" or malware. Such usage violates the spirit of the project and could lead to uncontrollable execution on your own machine.

### License & Attribution
If you use Karl to generate code or content for public projects, follow the licenses of the models you are using (e.g., DeepSeek's license) and respect the intellectual property of the documents in your Codex library.

---

## 4. Technical Hardening Checklist

- [x] **Offline Enforcement:** Set `HF_HUB_OFFLINE=1` to prevent unwanted network calls.
- [x] **Visible Diffs:** Always show changes before writing to disk.
- [x] **Docker Sandboxing:** (In Progress) Run unit tests and verifiers inside isolated containers.
- [ ] **Bridge Authentication:** Implement a shared secret/token for WebSocket connections.
- [x] **Path Sanitization:** Prevent directory traversal in model and file loading.

---

*Remember: Karl is a surgical instrument. Use it with the same care you would use with any powerful developer tool.*
