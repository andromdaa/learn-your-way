@AGENTS.md

## Claude Code specific
- Default to plan mode for any multi-file change
- /clear between unrelated tasks

## NixOS environment

This machine runs NixOS with direnv + nix-direnv. The `flake.nix` dev
shell activates automatically on `cd` (after `direnv allow`), providing
nixpkgs-linked `ruff`, `mypy`, and `python312`.

Run tools directly — no `uv run` or `nix develop --command` prefix needed:

```bash
uv sync --extra dev
ruff check .
ruff format .
mypy
pytest --cov
```

Always launch `claude` from within this directory so the direnv
environment is inherited.
