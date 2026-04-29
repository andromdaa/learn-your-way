{
  description = "My project with devenv + ruff-pre-commit";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    devenv.url = "github:cachix/devenv";
    git-hooks.url = "github:cachix/git-hooks.nix";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, devenv, git-hooks, flake-utils, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      hookConfig = git-hooks.lib.${system}.run {
        src = ./.;

        hooks = {
          trailing-whitespace.enable = true;
          end-of-file-fixer.enable = true;
          check-yaml.enable = true;
          check-toml.enable = true;

          ruff = {
            enable = true;
            settings.args = [ "--fix" ];
          };

          ruff-format.enable = true;

          mypy = {
            enable = true;
            settings = {
              args = [ "--strict" ];
              extraPackages = with pkgs.python3Packages; [
                pydantic
                pydantic-settings
                structlog
                pytest
              ];
            };
          };
        };
      };
    in
    {
      checks.pre-commit = hookConfig;
      devShells.default = devenv.lib.mkShell {
        inherit inputs pkgs;

        modules = [
          ({ pkgs, lib, config, ... }: {
            packages = [
              pkgs.python312
              pkgs.ruff
              pkgs.python3Packages.mypy
            ];

            # Enable git hooks managed by devenv.
            git-hooks = {
              enable = true;
              # Optional: run hooks automatically on enter.
              install.enable = true;

              hooks = {
                trailing-whitespace.enable = true;
                end-of-file-fixer.enable = true;
                check-yaml.enable = true;
                check-toml.enable = true;

                ruff = {
                  enable = true;
                  settings.args = [ "--fix" ];
                };

                ruff-format.enable = true;

                mypy = {
                  enable = true;
                  settings = {
                    args = [ "--strict" ];
                    extraPackages = with pkgs.python3Packages; [
                      pydantic
                      pydantic-settings
                      structlog
                      pytest
                    ];
                  };
                };
              };
            };

            enterShell = ''
              echo "devenv shell ready"
            '';
          })
        ];
      };
    };
}
# {
#   description = "learn-your-way-oss dev shell";

#   inputs = {
#     nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
#     flake-utils.url = "github:numtide/flake-utils";
#   };

#   outputs =
#     { nixpkgs, flake-utils, ... }:
#     flake-utils.lib.eachDefaultSystem (
#       system:
#       let
#         pkgs = import nixpkgs { inherit system; };
#       in
#       {
#         devShells.default = pkgs.mkShell {
#           packages = with pkgs; [
#             python312
#             uv
#             ruff
#             mypy
#           ];

#           shellHook = ''
#             export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
#             uv sync --extra dev --quiet
#           '';
#         };
#       }
#     );
# }
