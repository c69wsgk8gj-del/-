#!/usr/bin/env python3
"""Install the project-scoped Codex skill without replacing existing files."""
import argparse
import shutil
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / '.agents/skills/hiring-panel'

def install(project):
    target = Path(project).resolve() / '.agents/skills/hiring-panel'
    if target.is_symlink():
        raise RuntimeError(f'Refusing symlink target: {target}')
    if target.exists():
        expected = {p.relative_to(SOURCE): p.read_bytes() for p in SOURCE.rglob('*') if p.is_file()}
        actual = {p.relative_to(target): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        if actual != expected:
            raise RuntimeError(f'Existing skill differs; no files changed: {target}')
        return target, 'already installed'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, target)
    return target, 'installed'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    args = parser.parse_args()
    path, status = install(args.project)
    print(f'{status}: {path}')
    print('Start a new Codex session in that project; invoke $hiring-panel with your resume and role.')
