{
  description = "SpeisePlan Home Assistant integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            commitizen # conventional commit authoring + the commit-msg hook
            ruff       # lint + format
          ];

          shellHook = ''
            git config core.hooksPath .githooks
          '';
        };

        formatter = pkgs.nixfmt-rfc-style;
      });
}
