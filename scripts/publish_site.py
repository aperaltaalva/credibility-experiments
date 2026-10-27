"""Publish the checked site tree to gh-pages without rewriting branch history."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
assert not git('status', '--porcelain'), 'Commit the intended changes before publishing.'
source = git('rev-parse', 'HEAD')
tree = git('rev-parse', 'HEAD:site')
parents = []
old = subprocess.run(['git', 'ls-remote', '--heads', 'origin', 'gh-pages'], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
if old:
    subprocess.run(['git', 'fetch', 'origin', 'gh-pages'], cwd=root, check=True)
    parents = ['-p', git('rev-parse', 'FETCH_HEAD')]
commit = git('commit-tree', tree, *parents, '-m', f'Publish experiment board from {source}')
subprocess.run(['git', 'push', 'origin', f'{commit}:refs/heads/gh-pages'], cwd=root, check=True)
print('Published site tree:', commit)
