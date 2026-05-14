import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from jinja2 import Environment, FileSystemLoader


class Repository(TypedDict):
    name: str
    description: str
    url: str
    repositoryTopics: list[dict[str, str]] | None
    stargazerCount: int


class Category(TypedDict):
    display_name: str
    icon: str
    repos: list[Repository]


class CategoryConfig(TypedDict):
    name: str
    icon: str
    keywords: list[str]


def fetch_repos(source: str) -> list[Repository]:
    repos: list[Repository] = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    return sorted(repos, key=lambda x: x["name"].lower())


def categorize_repos(repos: list[Repository]) -> dict[str, Category]:
    category_configs: dict[str, CategoryConfig] = {
        "php": {
            "name": "PHP",
            "icon": "fa-brands fa-php",
            "keywords": [
                "php",
                "symfony",
                "laravel",
                "composer",
            ],
        },
        "rust": {
            "name": "Rust",
            "icon": "fa-brands fa-rust",
            "keywords": [
                "rust",
                "cargo",
            ],
        },
        "docker": {
            "name": "Docker",
            "icon": "fa-brands fa-docker",
            "keywords": [
                "docker",
                "dockerfile",
                "docker-compose",
            ],
        },
        "typescript": {
            "name": "TypeScript",
            "icon": "fa-brands fa-js",
            "keywords": [
                "typescript",
                "ts",
            ],
        },
        "javascript": {
            "name": "JavaScript",
            "icon": "fa-brands fa-square-js",
            "keywords": [
                "javascript",
                "js",
                "node",
                "chrome-extension",
            ],
        },
        "python": {
            "name": "Python",
            "icon": "fa-brands fa-python",
            "keywords": [
                "python",
                "django",
                "flask",
                "fastapi",
                "uv",
                "pip",
            ],
        },
        "go": {
            "name": "Go",
            "icon": "fa-brands fa-golang",
            "keywords": [
                "go",
                "golang",
            ],
        },
        "shell": {
            "name": "Shell",
            "icon": "fa-solid fa-terminal",
            "keywords": [
                "shell",
                "bash",
                "zsh",
                "fish",
                "dotfiles",
            ],
        },
        "other": {
            "name": "Other",
            "icon": "fa-solid fa-box-open",
            "keywords": [],
        },
    }

    categories: dict[str, Category] = {
        k: {
            "display_name": v["name"],
            "icon": v["icon"],
            "repos": [],
        }
        for k, v in category_configs.items()
    }

    for repo in repos:
        raw_topics = repo.get("repositoryTopics")
        topics: list[str] = [t["name"].lower() for t in raw_topics] if raw_topics else []
        repo_name_lower = repo["name"].lower()
        repo_desc_lower = (repo.get("description") or "").lower()

        matched_category = "other"
        
        for cat_id, config in category_configs.items():
            if cat_id == "other":
                continue

            if any(kw in topics for kw in config["keywords"]):
                matched_category = cat_id
                break
        
        if matched_category == "other":
            for cat_id, config in category_configs.items():
                if cat_id == "other":
                    continue
                
                if cat_id == "go":
                    if "golang" in repo_name_lower or "golang" in repo_desc_lower or \
                       repo_name_lower.startswith("go-") or repo_name_lower.endswith("-go"):
                        matched_category = cat_id
                        break
                    continue

                if any(kw in repo_name_lower for kw in config["keywords"]) or \
                   any(kw in repo_desc_lower for kw in config["keywords"]):
                    matched_category = cat_id
                    break

        categories[matched_category]["repos"].append(repo)

    return {
        k: v for k, v in sorted(categories.items()) if v["repos"]
    }


def generate_registry(categories: dict[str, Category]) -> None:
    env: Environment = Environment(
        loader=FileSystemLoader("templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    
    last_updated: str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    readme_template = env.get_template("README.md.j2")
    readme_content: str = readme_template.render(
        categories=categories,
        last_updated=last_updated,
    )
    Path("README.md").write_text(readme_content, encoding="utf-8")

    index_template = env.get_template("index.html.j2")
    
    all_repos = []
    for cat in categories.values():
        all_repos.extend(cat["repos"])
        
    index_content: str = index_template.render(
        repos_json=json.dumps(all_repos),
    )
    Path("index.html").write_text(index_content, encoding="utf-8")


def main() -> None:
    source = "repos.json"
    if not Path(source).exists():
        print(f"Error: {source} not found.", file=sys.stderr)
        sys.exit(1)
        
    repos: list[Repository] = fetch_repos(source)
    categories: dict[str, Category] = categorize_repos(repos)
    generate_registry(categories)


if __name__ == "__main__":
    main()
