#!/usr/bin/env python3
"""The gates AGENTS.md describes, runnable locally and in CI.

Usage: python3 scripts/lint.py [substring-of-check-name]

Exit code is 0 when every check passed, 1 otherwise. Each check prints its own
verdict so a failure names itself. Gate design follows khasky/awesome-agent-skills
(MIT), trimmed to the rules this repository states.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
EVAL_FILES = ("eval_queries.json", "evals.json")

DESCRIPTION_MAX = 300   # every installed description loads into every session
SKILL_LINES_MAX = 500   # SKILL.md is the map; detail belongs in references/
SKILL_WORDS_MAX = 5000  # lines undercount long lines; words track what a run pays
REFERENCE_LINES_MAX = 200
LANGUAGE_EXAMPLES_THRESHOLD = 3


# --- file discovery ---------------------------------------------------------

_FILES: list[str] = []


def files() -> list[str]:
    """Paths git tracks, so the gate sees what a clean checkout sees.

    Outside a git repository (or before the first `git add`) every file under
    the root counts instead, so the gates never pass vacuously.
    """
    if not _FILES:
        run = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
        listed = [line.strip() for line in run.stdout.splitlines() if line.strip()]
        if run.returncode != 0 or not listed:
            listed = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                      if p.is_file() and ".git" not in p.relative_to(ROOT).parts]
        _FILES.extend(sorted(listed))
    return _FILES


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def skill_dirs() -> list[pathlib.Path]:
    names = {p.split("/")[1] for p in files() if p.startswith("skills/") and p.count("/") >= 2}
    return sorted(SKILLS / name for name in names)


def skill_markdown(folder: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in [folder / "SKILL.md", *sorted((folder / "references").glob("*.md"))] if p.exists()]


def references() -> list[str]:
    return [p for p in files() if p.startswith("skills/") and p.count("/") == 3
            and p.split("/")[2] == "references"]


def frontmatter(path: pathlib.Path) -> dict[str, str] | None:
    lines = read(path).splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in lines[1:]:
        return None
    end = lines.index("---", 1)
    keys = {}
    for line in lines[1:end]:
        match = re.match(r"^([a-z_]+):(.*)$", line)
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        return value[1:-1]
    return value


# --- the checks -------------------------------------------------------------
# Each returns a list of failure lines; empty means the gate passed.

def frontmatter_is_valid() -> list[str]:
    fail = []
    for folder in skill_dirs():
        path = folder / "SKILL.md"
        if not path.exists():
            fail.append(f"{rel(folder)}: no SKILL.md")
            continue
        keys = frontmatter(path)
        if keys is None:
            fail.append(f"{rel(path)}: missing or unclosed frontmatter")
            continue
        for required in ("name", "description", "license", "metadata"):
            if required not in keys:
                fail.append(f"{rel(path)}: missing '{required}'")
        if "name" in keys and unquote(keys["name"]) != folder.name:
            fail.append(f"{rel(path)}: name does not match folder '{folder.name}'")
        if "description" in keys:
            raw = keys["description"]
            if raw[:1] in "\"'" and (len(raw) < 2 or raw[-1] != raw[0]):
                fail.append(f"{rel(path)}: unbalanced quoting in description")
            description = unquote(raw)
            if not description:
                fail.append(f"{rel(path)}: empty description - nothing to trigger on")
            elif len(description) > DESCRIPTION_MAX:
                fail.append(f"{rel(path)}: description is {len(description)} chars (max {DESCRIPTION_MAX})")
    return fail


def code_fences_are_balanced() -> list[str]:
    fail = []
    for p in files():
        if p.endswith(".md") and (ROOT / p).exists():
            count = len(re.findall(r"^```", read(ROOT / p), re.M))
            if count % 2:
                fail.append(f"{p}: unbalanced code fences ({count})")
    return fail


def skills_ship_markdown_only() -> list[str]:
    fail = []
    for p in files():
        if not p.startswith("skills/") or p.count("/") < 2:
            continue
        parts = p.split("/")
        if parts[2] == "SKILL.md" and len(parts) == 3:
            continue
        if parts[2] == "references" and len(parts) == 4 and p.endswith(".md"):
            continue
        if parts[2] == "evals" and len(parts) == 4 and parts[3] in EVAL_FILES:
            continue
        fail.append(f"{p}: a skill holds SKILL.md, references/*.md and evals/{{{','.join(EVAL_FILES)}}} only")
    return fail


def referenced_files_exist() -> list[str]:
    fail = []
    for folder in skill_dirs():
        for path in skill_markdown(folder):
            base = folder if path.name == "SKILL.md" else folder / "references"
            for target in sorted(set(re.findall(r"\]\(([^)#\s]+\.md)\)", read(path)))):
                if "://" not in target and not (base / target).exists():
                    fail.append(f"{rel(path)}: links to missing file {target}")
    return fail


def references_are_reachable() -> list[str]:
    fail = []
    for p in references():
        name, skill = p.split("/")[3], p.split("/")[1]
        others = [ROOT / q for q in files() if q.startswith(f"skills/{skill}/") and q.endswith(".md") and q != p]
        if not any(name in read(q) for q in others if q.exists()):
            fail.append(f"{p}: nothing in its skill names it - link it where it is needed")
    return fail


def sibling_skill_mentions_resolve() -> list[str]:
    # A handoff to a sibling is written as `skill-name` in backticks; a renamed
    # or never-written sibling leaves the reader nowhere to go. A backticked
    # kebab-case name counts as a skill mention when it sits next to the word
    # "skill" or ends like an existing skill name does (`-best-practices`).
    names = {folder.name for folder in skill_dirs()}
    suffixes = tuple({"-" + n.split("-")[-1] for n in names})
    kebab = r"`([a-z0-9]+(?:-[a-z0-9]+)+)`"
    near_skill = re.compile(rf"{kebab}\s+skill|skill\s+{kebab}", re.I)
    fail = []
    for folder in skill_dirs():
        for path in skill_markdown(folder):
            text = read(path)
            mentioned = {t for t in re.findall(kebab, text) if t.endswith(suffixes)}
            mentioned |= {a or b for a, b in near_skill.findall(text)}
            for token in sorted(mentioned - names):
                fail.append(f"{rel(path)}: names sibling skill `{token}`, which does not exist")
    return fail


def single_language_skills_map_across() -> list[str]:
    langs = {"typescript", "ts", "javascript", "js", "jsx", "tsx", "python", "py", "go", "golang",
             "rust", "rs", "java", "kotlin", "csharp", "cs", "ruby", "rb", "php", "swift", "cpp", "c"}
    marker = re.compile(r"^(#{1,6} |[-*] )?\*{0,2}other (languages|runtimes|ecosystems|stacks|frameworks)",
                        re.I | re.M)
    fail = []
    for folder in skill_dirs():
        text = "".join(read(p) for p in skill_markdown(folder))
        seen = {lang.lower() for lang in re.findall(r"^```([A-Za-z+#]+)", text, re.M) if lang.lower() in langs}
        total = sum(1 for lang in re.findall(r"^```([A-Za-z+#]+)", text, re.M) if lang.lower() in langs)
        if total >= LANGUAGE_EXAMPLES_THRESHOLD and len(seen) == 1 and not marker.search(text):
            fail.append(f"{folder.name}: {total} code examples, all {seen.pop()}, and no "
                        f"'Other languages/runtimes/frameworks' mapping")
    return fail


def skill_budgets() -> list[str]:
    fail = []
    for folder in skill_dirs():
        path = folder / "SKILL.md"
        if not path.exists():
            continue
        text = read(path)
        lines, words = len(text.splitlines()), len(text.split())
        if lines > SKILL_LINES_MAX:
            fail.append(f"{rel(path)}: {lines} lines (budget {SKILL_LINES_MAX}) - move detail into references/")
        if words > SKILL_WORDS_MAX:
            fail.append(f"{rel(path)}: {words} words (budget {SKILL_WORDS_MAX}) - move detail into references/")
    return fail


def reference_budget() -> list[str]:
    fail = []
    for p in references():
        lines = len(read(ROOT / p).splitlines())
        if lines > REFERENCE_LINES_MAX:
            fail.append(f"{p}: {lines} lines (budget {REFERENCE_LINES_MAX}) - split it by topic")
    return fail


def no_per_skill_readme() -> list[str]:
    return [f"{p}: remove; SKILL.md is the only per-skill document"
            for p in files() if p.startswith("skills/") and p.endswith("/README.md")]


def eval_sets_are_well_formed() -> list[str]:
    fail = []
    names = {folder.name for folder in skill_dirs()}
    for p in files():
        if not (p.startswith("skills/") and "/evals/" in p):
            continue
        parts = p.split("/")
        skill, filename = parts[1], parts[-1]
        if len(parts) != 4 or filename not in EVAL_FILES:
            continue  # reported by skills_ship_markdown_only
        try:
            data = json.loads(read(ROOT / p))
        except json.JSONDecodeError as exc:
            fail.append(f"{p}: invalid JSON - {exc}")
            continue

        if filename == "eval_queries.json":
            if not isinstance(data, list) or not data:
                fail.append(f"{p}: expected a non-empty list of queries")
                continue
            seen: set[str] = set()
            for i, case in enumerate(data):
                query = case.get("query") if isinstance(case, dict) else None
                if not isinstance(query, str) or not query.strip():
                    fail.append(f"{p}: case {i} has no query")
                    continue
                if query in seen:
                    fail.append(f"{p}: duplicate query {query[:40]!r}")
                seen.add(query)
                if not isinstance(case.get("should_trigger"), bool):
                    fail.append(f"{p}: case {i} has no should_trigger boolean")
                sibling = case.get("belongs_to")
                if sibling is not None and sibling not in names:
                    fail.append(f"{p}: case {i} sends belongs_to to a missing skill: {sibling}")
                if sibling == skill:
                    fail.append(f"{p}: case {i} hands a negative back to the skill under test")
                if case.get("split") not in ("train", "validation"):
                    fail.append(f"{p}: case {i} has split {case.get('split')!r}, expected train or validation")
            verdicts = {case.get("should_trigger") for case in data if isinstance(case, dict)}
            if not {True, False} <= verdicts:
                fail.append(f"{p}: a trigger set needs both positive and negative queries")
            continue

        if not isinstance(data, dict) or data.get("skill_name") != skill:
            fail.append(f"{p}: skill_name must be {skill!r}")
            continue
        cases = data.get("evals")
        if not isinstance(cases, list) or not cases:
            fail.append(f"{p}: no eval cases")
            continue
        for i, case in enumerate(cases):
            if not isinstance(case, dict) or not str(case.get("prompt", "")).strip():
                fail.append(f"{p}: case {i} has no prompt")
                continue
            for n, check in enumerate(case.get("checks") or []):
                where = f"{p}: case {i} check {n}"
                pattern = check.get("pattern") if isinstance(check, dict) else None
                passes = check.get("pass") if isinstance(check, dict) else None
                fails = check.get("fail") if isinstance(check, dict) else None
                if not isinstance(pattern, str) or not passes or not fails \
                        or not isinstance(passes, list) or not isinstance(fails, list):
                    fail.append(f"{where}: needs a pattern and non-empty pass and fail lists")
                    continue
                try:
                    compiled = re.compile(pattern)
                except re.error as exc:
                    fail.append(f"{where}: pattern does not compile - {exc}")
                    continue
                fail += [f"{where}: pattern misses pass example {t[:40]!r}" for t in passes if not compiled.search(t)]
                fail += [f"{where}: pattern matches fail example {t[:40]!r}" for t in fails if compiled.search(t)]
    return fail


CHECKS = [
    ("skill frontmatter is valid", frontmatter_is_valid),
    ("code fences are balanced", code_fences_are_balanced),
    ("skills ship Markdown only", skills_ship_markdown_only),
    ("no per-skill README", no_per_skill_readme),
    ("linked files exist", referenced_files_exist),
    ("every reference file is named somewhere", references_are_reachable),
    ("sibling skill mentions resolve", sibling_skill_mentions_resolve),
    ("single-language skills carry a mapping", single_language_skills_map_across),
    ("SKILL.md stays inside its budgets", skill_budgets),
    ("references stay inside the line budget", reference_budget),
    ("eval sets are well formed", eval_sets_are_well_formed),
]


def main(argv: list[str]) -> int:
    only = argv[1] if len(argv) > 1 else None
    failed = 0
    for name, check in CHECKS:
        if only and only not in name:
            continue
        problems = check()
        failed += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {name}")
        for line in problems:
            print(f"      {line}")
    if failed:
        print(f"\n{failed} of {len(CHECKS)} checks failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
