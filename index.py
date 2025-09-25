#!/usr/bin/env python3
"""
Print a sorted list of top-level .py filenames in the utilities-project directory,
excluding this file (index.py).
"""

from pathlib import Path


def list_top_level_py_files(target_dir: Path) -> list[str]:
    exclude = {'index.py'}
    return sorted(p.name for p in target_dir.glob('*.py') if p.is_file() and p.name not in exclude)


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    for name in list_top_level_py_files(project_dir):
        print(name)


if __name__ == '__main__':
    main()
