import os
import stat

from conftest import run_e


def socket_file(path):
    os.mknod(path, stat.S_IFSOCK | 0o600)


def test_gc_only_removes_stale_ipc_sockets(tmp_path, fake_proc):
    runtime = tmp_path / "run"
    runtime.mkdir()
    live = runtime / "vscode-ipc-live.sock"
    stale = runtime / "vscode-ipc-stale.sock"
    git = runtime / "vscode-git-keep.sock"
    regular = runtime / "vscode-ipc-regular.sock"
    socket_file(live)
    socket_file(stale)
    socket_file(git)
    regular.write_text("keep")
    fake_proc.add_listening(str(live))
    fake_proc.write()
    result = run_e(["--gc"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_RUNTIME_DIR": runtime})
    assert result.returncode == 0
    assert live.exists() and not stale.exists() and git.exists() and regular.exists()
    assert "removed 1 stale" in result.stdout or "removed 1 stale" in result.stderr


def test_gc_dry_run_only_lists_stale_ipc_sockets(tmp_path, fake_proc):
    runtime = tmp_path / "run"
    runtime.mkdir()
    live = runtime / "vscode-ipc-live.sock"
    stale = runtime / "vscode-ipc-stale.sock"
    git = runtime / "vscode-git-keep.sock"
    regular = runtime / "vscode-ipc-regular.sock"
    socket_file(live)
    socket_file(stale)
    socket_file(git)
    regular.write_text("keep")
    fake_proc.add_listening(str(live))
    fake_proc.write()
    result = run_e(["--gc", "--dry-run"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_RUNTIME_DIR": runtime})
    assert result.returncode == 0
    assert live.exists() and stale.exists() and git.exists() and regular.exists()
    assert f"would remove: {stale}" in result.stdout
    assert "would remove 1 stale" in result.stdout
