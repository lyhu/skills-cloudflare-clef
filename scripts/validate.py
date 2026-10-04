#!/usr/bin/env python3
"""Validate skill packaging, YAML/JSON syntax, schemas, and Python syntax."""

import ast
import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "cloudflare-clef"
SKILLS = [SKILL, ROOT / "skills" / "ego-clef"]


def validate_skill(skill, root_package):
    content = (skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md requires YAML frontmatter")
    frontmatter = yaml.safe_load(match.group(1))
    allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    if not isinstance(frontmatter, dict) or set(frontmatter) - allowed:
        raise ValueError("Invalid frontmatter fields")
    name = frontmatter.get("name", "")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Invalid skill name")
    if name != skill.name or len(name) > 64:
        raise ValueError("Skill name must match its directory and be at most 64 characters")
    description = frontmatter.get("description")
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1024:
        raise ValueError("Invalid skill description")
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()
    ):
        raise ValueError("metadata must be a string-to-string mapping")
    skill_package = json.loads((skill / "package.json").read_text())
    if root_package["version"] != skill_package["version"] or metadata["version"] != root_package["version"]:
        raise ValueError("Package and skill versions must match")
    if {frontmatter["license"], root_package["license"], skill_package["license"]} != {"Apache-2.0"}:
        raise ValueError("License metadata must agree")


def main():
    root_package = json.loads((ROOT / "package.json").read_text())
    if root_package.get("pi", {}).get("skills") != ["./skills/" + skill.name for skill in SKILLS]:
        raise ValueError("Pi package must reference both distributed skill directories")
    for skill in SKILLS:
        validate_skill(skill, root_package)
    for file in ROOT.rglob("*.py"):
        if not {".venv", "node_modules", ".local"}.intersection(file.parts):
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    schema = json.loads((SKILL / "references" / "primitives.json").read_text())
    Draft202012Validator.check_schema(schema)
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    if not isinstance(workflow.get("jobs"), dict):
        raise ValueError("CI workflow requires jobs")
    required = [
        ROOT / "README.md", ROOT / "LICENSE", SKILL / "scripts" / "evaluate.py",
        SKILL / "scripts/log_stats.py", SKILL / "references/logging.md",
        SKILL / "templates" / "client.py", SKILL / "templates" / "client.ts",
        ROOT / "skills/ego-clef/scripts/browser.mjs",
        ROOT / "skills/ego-clef/scripts/browser-log.mjs",
        ROOT / "skills/ego-clef/scripts/semantic.mjs",
        ROOT / "skills/ego-clef/scripts/install-browser.py",
        ROOT / "skills/ego-clef/references/browser.md",
    ]
    if any(not path.is_file() or not path.stat().st_size for path in required):
        raise ValueError("Missing or empty deliverable")
    print("Skill metadata, packaging, schemas, workflow, and Python syntax are valid.")


if __name__ == "__main__":
    main()
