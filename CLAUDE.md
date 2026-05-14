# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

Static-site generator that publishes a categorized list of the user's public GitHub repos. Produces two artifacts from the same generator, but they live on different branches:

- `README.md` — rendered table grouped by language category. Lives on `main` (so GitHub renders it on the repo landing page). Links to the live web view.
- `index.html` — single-page site with fuzzy-search UI. Lives on `gh-pages` only. Served via GitHub Pages at `https://k0pernikus.github.io/registry/`.

Both are NOT hand-edited; treat them as build outputs.

## Branch topology

| Branch | What it carries | Who writes it |
|---|---|---|
| `main` | Source code, templates, `README.md` | Humans push source changes; CI pushes regenerated `README.md` with `[skip ci]` |
| `gh-pages` | Rendered `index.html` + a copy of `README.md` (docsify fetches it at runtime) | CI only — orphan branch, fully regenerated each run |

`index.html` is gitignored on `main` so local renders don't pollute the working tree. The only place `index.html` is committed is `gh-pages`.

## Pipeline

`gh repo list` → `repos.json` → `src/generate.py` → renders `templates/*.j2` → writes `README.md` + `index.html`.

- `repos.json` is the input data and is **gitignored** (regenerated each run). Don't commit it. All `*.json` is gitignored — no JSON artefacts belong in the tree.
- `index.html` is **gitignored on main**. It's only committed to `gh-pages` by CI.
- Entry point is `src/generate.py`. Run it via `mise run render` (or `uv run python src/generate.py`).
- Categorization (in `categorize_repos`): first pass matches GitHub topics against per-category keywords; second pass falls back to repo name/description substring matches. The `go` category has a special-case to avoid matching the substring `go` in unrelated repos (requires `golang` or `go-`/`-go` boundaries). Adding a new language category means adding both an entry in `CATEGORY_RULES` and any name-heuristic exceptions.

## Common commands

All tasks go through `mise` (defined in `mise.toml`):

| Task | What it does |
|---|---|
| `mise run fetch` | `gh repo list k0pernikus … > repos.json` |
| `mise run render` | `uv run python src/generate.py` (regenerate `README.md` + `index.html` from `repos.json`) |
| `mise run generate` | `fetch` + `render` |
| `mise run check` | `ruff check src && ty check src` |
| `mise run format` | `ruff format src` |
| `mise run serve` | `python -m http.server 3000` for previewing `index.html` locally |

Tools (`uv`, `gh`, `lefthook`) are pinned in `mise.toml` — install with `mise install`, not the system package manager.

Lefthook hooks (installed automatically on `mise install` via the `postinstall` hook):

- `pre-commit`: `mise run check`
- `pre-push`: `mise run check` (generator runs in CI; local pre-push only validates lint/types)

## Editing rules specific to this repo

- **Don't edit `README.md` or `index.html` directly.** Edit the templates in `templates/` and re-render.
- **Don't commit `repos.json` or `index.html` on `main`.** Both are gitignored. CI publishes `index.html` to `gh-pages`.
- **Never push to `gh-pages` from a local machine.** It's a CI-owned orphan branch — manual pushes will be clobbered on the next CI run.
- The `update-registry.yml` workflow commits the main-branch README with `[skip ci]` to avoid loops — preserve that marker if touching the workflow. Pushes to `gh-pages` don't trigger this workflow (only `main` does), so no marker needed there.
- Python target is **3.15** (`requires-python = ">=3.15"`, `target-version = "py315"`). Use modern syntax (`X | Y` unions, `list[T]`, etc.).
