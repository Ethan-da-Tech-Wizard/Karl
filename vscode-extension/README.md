# Karl VS/OSS Code Extension

Karl adds a local coding cockpit for the Karl desktop bridge.

## Main Surfaces

- **Swarm**: compose workspace tasks, refactors, reviews, and test-generation jobs.
- **Chat**: ask Karl direct questions with live introspection streaming.
- **Changes**: review proposed file edits before applying them.
- **Knowledge**: ingest files or folders into Karl's local RAG index.
- **Lab**: run prompt A/B comparisons through the local bridge.
- **Models**: inspect and activate local model registry entries.
- **Codex**: browse local reference material exposed by Karl.

## Safety Model

Karl no longer writes swarm edits immediately from bridge notifications. Proposed
edits enter the **Changes** queue first. Use **Preview** to open a diff against a
temporary proposed file, **Apply** to write the real file with a `.original`
backup, or **Reject** to discard the pending edit.

## Commands

- `Karl: Open Karl Panel`
- `Karl: Ask Karl to Refactor Selection`
- `Karl: Explain Selection`
- `Karl: Generate Tests for Active File`
- `Karl: Review Active File`
- `Karl: Ask About Workspace`
- `Karl: Ingest Active File into Knowledge Base`
- `Karl: Ingest Workspace Folder into Knowledge Base`

The extension expects the Karl desktop bridge to be listening on the configured
`karl.port`, defaulting to `8080`.
