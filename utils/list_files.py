import subprocess
from pathlib import Path

import pathspec

SUFFIXES = (".py", ".html", ".js", ".txt", ".ini", ".toml", ".md", ".json")


def load_gitignore_patterns(gitignore_path: Path) -> pathspec.PathSpec:
    """Load .gitignore patterns."""
    with gitignore_path.open("r", encoding="utf-8") as file:
        lines = file.readlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def output_file_content(file: Path, startpath: Path, output) -> None:
    """Output the file path relative to the project root and its source in Markdown format."""
    output.write(f"## {file.relative_to(startpath)}\n\n")
    output.write(
        "```python\n"
        if file.suffix == ".py"
        else "```html\n"
        if file.suffix == ".html"
        else "```js\n"
        if file.suffix == ".js"
        else "```json\n"
        if file.suffix == ".json"
        else "```txt\n",
    )
    try:
        with file.open("r", encoding="utf-8") as f:
            output.write(f.read())
    except UnicodeDecodeError as e:
        output.write(f"Error reading {file}: {e}")
    output.write("\n```\n\n")


def list_files(startpath: Path, output_file_path: Path) -> None:
    """List all files with the specified extensions in the project in Markdown format."""
    gitignore_path = startpath / ".gitignore"
    ignore_patterns = (
        load_gitignore_patterns(gitignore_path)
        if gitignore_path.exists()
        else pathspec.PathSpec([])
    )

    with output_file_path.open("w", encoding="utf-8") as output:
        output.write("# Project Source Files\n\n")
        for file in startpath.rglob("*"):
            if not file.is_file():
                continue
            relative_path = file.relative_to(startpath)
            if any(
                part.startswith(".") and part != ".vscode"
                for part in relative_path.parts
            ):
                continue
            if ignore_patterns.match_file(relative_path):
                continue
            if file.suffix in SUFFIXES:
                output_file_content(file, startpath, output)

        output.write("# Git Log\n\n")
        output.write("```\n")
        try:
            git_log = subprocess.check_output(
                ["git", "log", '--pretty=format:"%ad | %s%d"', "--date=short"],
                cwd=startpath,
                text=True,
                encoding="utf-8",
            )
            output.write(git_log)
        except subprocess.CalledProcessError as e:
            output.write(f"Error fetching git log: {e}")
        output.write("\n```\n")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    output_file_path = project_root / "file_listings.md"
    list_files(project_root, output_file_path)
