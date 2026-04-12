# Changelog

All notable user-facing changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Changed
- Architecture documentation now cleanly separates stable architecture reference from internal development history.
- Main window now supports three area modes: preview only, split view, or editor only.
- Split view opens editor and preview side-by-side with draggable divider and equal default width.
- Markdown editing in the new write area saves debounced live to the selected file.
- Save state in the editor is now clearly visible as Unsaved, Saving, and Saved.

### Added
- Public-facing changelog workflow and PR checklist for clearer release communication.
- Ctrl+N now opens a system dialog to create a new markdown file with default starter content.
