{
  description = "learn-your-way-oss dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python313.withPackages (ps: with ps; [
          # ---- Runtime -------------------------------------------------------
          aiosqlite
          httpx
          pydantic
          pydantic-settings
          qdrant-client
          redis
          hiredis         # pulled in via redis[hiredis]
          structlog

          # ---- Dev / test ----------------------------------------------------
          pytest
          pytest-cov
          pytest-asyncio
          mypy
          pydantic
          testcontainers
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            python
            pkgs.ruff
            pkgs.pre-commit
          ];

          shellHook = ''
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
            pre-commit install --install-hooks 2>/dev/null
          '';
        };
      }
    );
}
