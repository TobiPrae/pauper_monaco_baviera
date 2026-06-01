# Agent scaffolding: repo-aware developer assistant

This folder contains minimal scaffolding for a repo-aware developer assistant.

Files
- `indexer.py`: simple AST-based indexer that extracts symbols from Python files.
- `memory.py`: small utilities to save/load JSON facts under `/memories/repo/`.
- `handlers.py`: helpers to produce unified diffs, list test files, and prepare commands.
- `git_workflow.py`: helpers to generate branch names and write patch files locally.

Usage

- Run the indexer to produce `repo_index.json`:

```bash
python -m agent.indexer .
```

- Use `agent.memory.save_fact("key", obj)` to persist repository facts under `/memories/repo/`.

- To propose a change, the assistant should produce a unified diff (via `handlers.propose_patch`) and call `git_workflow.write_patch` to write it locally. The user must approve before applying.

Provider-agnostic: pair this code with the `AGENT_PROMPT.md` prompt to instantiate the assistant in any LLM/chat UI.

The agent prompt is available at `agent/AGENT_PROMPT.md` in this repository. Drop that file into your assistant's system prompt or paste its contents when instantiating a provider-agnostic developer assistant.
