# Blattwerk Language Tools

VS Code extension for Blattwerk markdown.

## Features (v1)

- syntax highlighting for Blattwerk block directives in markdown
- snippets for frontmatter and common block types
- folding ranges for Frontmatter and `:::` blocks
- diagnostics from Python validator bridge (`app.cli.blatt_diagnostics_cli`)

## Development Setup (Dev Host)

1. Open this folder in VS Code.
2. Run `npm install`.
3. Run `npm run build`.
4. Press `F5` to start Extension Development Host.

## Install as VSIX

1. In this folder run `npm install` and `npm run build`.
2. Run `npx @vscode/vsce package`.
3. In VS Code: `Extensions: Install from VSIX...` and pick the generated `.vsix`.

## Diagnostics Bridge Configuration

- `blattwerk.diagnostics.pythonCommand`: Python executable path.
- `blattwerk.diagnostics.cliModule`: defaults to `app.cli.blatt_diagnostics_cli`.
- `blattwerk.diagnostics.extraArgs`: optional additional CLI args.

For this repository, set python command to the project venv, e.g.:

`a:/7thCloud/.venv/Scripts/python.exe`

Diagnostics run with workspace root as current directory, so imports resolve against the repository.
