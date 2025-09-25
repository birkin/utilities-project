"""
Print a sorted list of top-level .py filenames in the utilities-project directory,
excluding this file (index.py).
"""

from pathlib import Path


def list_top_level_py_files(target_dir: Path) -> list[str]:
    """
    Returns a sorted list of top-level .py filenames, excluding index.py.
    """
    exclude: set[str] = {"index.py"}
    return sorted(
        p.name
        for p in target_dir.glob("*.py")
        if p.is_file() and p.name not in exclude
    )


def main() -> None:
    """
    Prints top-level .py filenames in the project directory.
    """
    project_dir: Path = Path(__file__).resolve().parent
    names: list[str] = list_top_level_py_files(project_dir)
    for name in names:
        print(name)


if __name__ == '__main__':
    main()
