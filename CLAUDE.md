# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo does

Static-site generator that publishes a categorized list of the user's public GitHub repos. Produces two artifacts at the repo root:

- `README.md` — rendered table grouped by language category, displayed on GitHub.
- `index.html` — single-page site with fuzzy search, published via GitHub Pages.

Both are committed back to `main` by the GitHub Actions workflow on push, on a monthly cron, or via `workflow_dispatch`. They are NOT hand-edited; treat them as build outputs.

## Pipeline

`gh repo list` → `repos.json` → `src/generate.py` → renders `templates/*.j2` → writes `README.md` + `index.html`.

- `repos.json` is the input data and is **gitignored** (regenerated each run). Don't commit it.
- `main.py` is a leftover stub — entry point is `src/generate.py`.
- Categorization (in `categorize_repos`): first pass matches GitHub topics against per-category keywords; second pass falls back to repo name/description substring matches. The `go` category has a special-case to avoid matching the substring `go` in unrelated repos (requires `golang` or `go-`/`-go` boundaries). Adding a new language category means adding both an entry in `category_configs` and any name-heuristic exceptions.

## Common commands

All tasks go through `mise` (defined in `mise.toml`):

| Task | What it does |
|---|---|
| `mise run fetch` | `gh repo list k0pernikus … > repos.json` |
| `mise run render` | `uv run python src/generate.py` (regenerate `README.md` + `index.html` from `repos.json`) |
| `mise run generate` | `fetch` + `render` |
| `mise run check` | `ruff check src && ty check src` |
| `mise run format` | `ruff format src` |
| `mise run serve` | `python -m http.server 3000` for previewing `index.html` |

Tools (`uv`, `gh`, `lefthook`) are pinned in `mise.toml` — install with `mise install`, not the system package manager.

Lefthook hooks (installed automatically on `mise install` via the `postinstall` hook):

- `pre-commit`: `mise run check`
- `pre-push`: `mise run check` + `mise run generate` (so pushed commits always carry the freshly regenerated `README.md` / `index.html`)

## Editing rules specific to this repo

- **Don't edit `README.md` or `index.html` directly.** Edit the templates in `templates/` and re-render.
- **Don't commit `repos.json`.** It's an input cache, regenerated on every CI run.
- The `update-registry.yml` workflow commits with `[skip ci]` to avoid loops — preserve that marker if touching the workflow.
- Python target is **3.15** (`requires-python = ">=3.15"`, `target-version = "py315"`). Use modern syntax (`X | Y` unions, `list[T]`, etc.).
