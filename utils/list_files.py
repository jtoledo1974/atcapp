from pathlib import Path


def output_file_content(file: Path, startpath: Path, output) -> None:
    """Output the file path relative to the project root and its source in Markdown format."""
    output.write(f"## {file.relative_to(startpath)}\n\n")
    output.write(
        "```python\n"
        if file.suffix == ".py"
        else "```html\n"
        if file.suffix == ".html"
        else "```js\n",
    )
    try:
        with file.open("r", encoding="utf-8") as f:
            output.write(f.read())
    except UnicodeDecodeError as e:
        output.write(f"Error reading {file}: {e}")
    output.write("\n```\n\n")


def list_files(startpath: Path, output_file_path: Path) -> None:
    """List all files with the specified extensions in the project in Markdown format.

    Only interested in files in the src subdir.
    """
    with output_file_path.open("w", encoding="utf-8") as output:
        output.write("# Project Source Files\n\n")
        for file in (startpath / "src").glob("**/*"):
            if file.suffix in (".py", ".html", ".js"):
                output_file_content(file, startpath, output)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    output_file_path = project_root / "file_listings.md"
    list_files(project_root, output_file_path)
