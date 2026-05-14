import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from jinja2 import Environment, FileSystemLoader


class Repository(TypedDict):
    name: str
    description: str
    url: str
    repositoryTopics: list[dict[str, str]] | None
    isFork: bool


class Category(TypedDict):
    display_name: str
    icon: str
    repos: list[Repository]


@dataclass(frozen=True)
class CategoryRule:
    id: str
    display_name: str
    icon: str
    topics: tuple[str, ...] = field(default_factory=tuple)
    name_substrings: tuple[str, ...] = field(default_factory=tuple)
    desc_substrings: tuple[str, ...] = field(default_factory=tuple)
    name_prefixes: tuple[str, ...] = field(default_factory=tuple)
    name_suffixes: tuple[str, ...] = field(default_factory=tuple)


OTHER_ID = "other"

CATEGORY_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        id="php",
        display_name="PHP",
        icon="fa-brands fa-php",
        topics=("php", "symfony", "laravel", "composer"),
        name_substrings=("php", "symfony", "laravel", "composer"),
        desc_substrings=("php", "symfony", "laravel", "composer"),
    ),
    CategoryRule(
        id="rust",
        display_name="Rust",
        icon="fa-brands fa-rust",
        topics=("rust", "cargo"),
        name_substrings=("rust", "cargo"),
        desc_substrings=("rust", "cargo"),
    ),
    CategoryRule(
        id="docker",
        display_name="Docker",
        icon="fa-brands fa-docker",
        topics=("docker", "dockerfile", "docker-compose"),
        name_substrings=("docker", "dockerfile", "docker-compose"),
        desc_substrings=("docker", "dockerfile", "docker-compose"),
    ),
    CategoryRule(
        id="typescript",
        display_name="TypeScript",
        icon="fa-brands fa-js",
        topics=("typescript", "ts"),
        name_substrings=("typescript", "ts"),
        desc_substrings=("typescript", "ts"),
    ),
    CategoryRule(
        id="javascript",
        display_name="JavaScript",
        icon="fa-brands fa-square-js",
        topics=("javascript", "js", "node", "chrome-extension"),
        name_substrings=("javascript", "js", "node", "chrome-extension"),
        desc_substrings=("javascript", "js", "node", "chrome-extension"),
    ),
    CategoryRule(
        id="python",
        display_name="Python",
        icon="fa-brands fa-python",
        topics=("python", "django", "flask", "fastapi", "uv", "pip"),
        name_substrings=("python", "django", "flask", "fastapi", "uv", "pip"),
        desc_substrings=("python", "django", "flask", "fastapi", "uv", "pip"),
    ),
    CategoryRule(
        id="go",
        display_name="Go",
        icon="fa-brands fa-golang",
        topics=("go", "golang"),
        name_substrings=("golang",),
        desc_substrings=("golang",),
        name_prefixes=("go-",),
        name_suffixes=("-go",),
    ),
    CategoryRule(
        id="shell",
        display_name="Shell",
        icon="fa-solid fa-terminal",
        topics=("shell", "bash", "zsh", "fish", "dotfiles"),
        name_substrings=("shell", "bash", "zsh", "fish", "dotfiles"),
        desc_substrings=("shell", "bash", "zsh", "fish", "dotfiles"),
    ),
)

OTHER_RULE = CategoryRule(
    id=OTHER_ID,
    display_name="Other",
    icon="fa-solid fa-box-open",
)

ALL_RULES: tuple[CategoryRule, ...] = (*CATEGORY_RULES, OTHER_RULE)


def fetch_repos(source: str) -> list[Repository]:
    repos: list[Repository] = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    return sorted(repos, key=lambda x: x["name"].lower())


def partition_repos(repos: list[Repository]) -> tuple[list[Repository], list[Repository]]:
    projects: list[Repository] = [r for r in repos if not r["isFork"]]
    forks: list[Repository] = [r for r in repos if r["isFork"]]
    return projects, forks


def _topic_match(rule: CategoryRule, topics: frozenset[str]) -> bool:
    return not topics.isdisjoint(rule.topics)


def _heuristic_match(rule: CategoryRule, name: str, desc: str) -> bool:
    return (
        any(s in name for s in rule.name_substrings)
        or any(s in desc for s in rule.desc_substrings)
        or any(name.startswith(p) for p in rule.name_prefixes)
        or any(name.endswith(s) for s in rule.name_suffixes)
    )


def _pick_category(topics: frozenset[str], name: str, desc: str) -> str:
    for rule in CATEGORY_RULES:
        if _topic_match(rule, topics):
            return rule.id
    for rule in CATEGORY_RULES:
        if _heuristic_match(rule, name, desc):
            return rule.id
    return OTHER_ID


def categorize_repos(repos: list[Repository]) -> dict[str, Category]:
    categories: dict[str, Category] = {rule.id: Category(display_name=rule.display_name, icon=rule.icon, repos=[]) for rule in ALL_RULES}

    for repo in repos:
        raw_topics = repo.get("repositoryTopics")
        topics: frozenset[str] = frozenset(t["name"].lower() for t in raw_topics) if raw_topics else frozenset()
        name = repo["name"].lower()
        desc = (repo.get("description") or "").lower()
        cat_id = _pick_category(topics, name, desc)
        categories[cat_id]["repos"].append(repo)

    return {k: v for k, v in sorted(categories.items()) if v["repos"]}


def generate_registry(project_cats: dict[str, Category], fork_cats: dict[str, Category], all_repos: list[Repository], readme_path: Path) -> None:
    env: Environment = Environment(
        loader=FileSystemLoader("templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    last_updated: str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    readme_template = env.get_template("README.md.j2")
    readme_path.write_text(
        readme_template.render(project_cats=project_cats, fork_cats=fork_cats, collapse_forks=False),
        encoding="utf-8",
    )
    Path("README.docsify.md").write_text(
        readme_template.render(project_cats=project_cats, fork_cats=fork_cats, collapse_forks=True),
        encoding="utf-8",
    )

    index_template = env.get_template("index.html.j2")
    Path("index.html").write_text(
        index_template.render(
            repos_json=json.dumps(all_repos),
            last_updated=last_updated,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the registry README and index.html.")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Render README.local.md (gitignored) instead of README.md. Use for local dev.",
    )
    args = parser.parse_args()

    source = "repos.json"
    if not Path(source).exists():
        print(f"Error: {source} not found.", file=sys.stderr)
        sys.exit(1)

    readme_path = Path("README.local.md") if args.local else Path("README.md")

    repos: list[Repository] = fetch_repos(source)
    projects, forks = partition_repos(repos)
    project_cats = categorize_repos(projects)
    fork_cats = categorize_repos(forks)
    generate_registry(project_cats, fork_cats, projects + forks, readme_path)


if __name__ == "__main__":
    main()
