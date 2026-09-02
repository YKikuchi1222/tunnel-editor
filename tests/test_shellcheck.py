import subprocess
from pathlib import Path


def test_shellcheck():
    root = Path(__file__).parents[1]
    result = subprocess.run([str(root / ".venv/bin/shellcheck"), "-x", "-s", "bash", "bin/e", "install.sh"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
