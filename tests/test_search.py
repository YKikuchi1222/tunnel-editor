import subprocess

from conftest import add_window, make_server, recorded, run_e


def setup_window(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-ext-1.sock"
    add_window(fake_proc, server, 200, sock, True, 20, 201, "/tmp/code-server")
    fake_proc.write()
    return sock


def git_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    (path / "sub").mkdir()
    (path / "sub" / "runner.py").write_text("two")
    (path / "other").mkdir()
    (path / "other" / "runner.py").write_text("three")
    subprocess.run(["git", "add", "."], cwd=path, check=True)


def test_unique_search_and_line_search(tmp_path, fake_proc):
    sock = setup_window(tmp_path, fake_proc)
    git_repo(tmp_path)
    record = tmp_path / "record"
    result = run_e(["runner.py:42"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 1  # two matches are intentionally ambiguous
    assert "  1) " in result.stderr
    assert "  2) " in result.stderr
    assert "sub/runner.py" in result.stderr
    assert "other/runner.py" in result.stderr
    (tmp_path / "sub" / "unique.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    result = run_e(["unique"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[-1][0] == sock.encode()


def test_search_from_subdirectory_resolves_absolute_and_goto_paths(tmp_path, fake_proc):
    sock = setup_window(tmp_path, fake_proc)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    sub = tmp_path / "sub"
    sub.mkdir()
    unique = sub / "test_gc.py"
    runner = sub / "runner.py"
    unique.write_text("x")
    runner.write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    record = tmp_path / "record"
    result = run_e(["test_gc"], sub, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[-1][-1] == unique.as_posix().encode()
    result = run_e(["runner.py:42"], sub, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[-1] == (sock.encode(), b"-r", b"-g", b"--", f"{runner}:42".encode())


def test_search_max_warns_and_prints_numbered_matches(tmp_path, fake_proc):
    setup_window(tmp_path, fake_proc)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for name in ("match-a.txt", "match-b.txt", "match-c.txt"):
        (tmp_path / name).write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    result = run_e(["match-"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_SEARCH_MAX": 2})
    assert result.returncode == 1
    assert "search results truncated at 2" in result.stderr
    assert "  1) match-a.txt" in result.stderr
    assert "  2) match-b.txt" in result.stderr


def test_search_case_and_new(tmp_path, fake_proc):
    sock = setup_window(tmp_path, fake_proc)
    git_repo(tmp_path)
    (tmp_path / "MixedCase.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    record = tmp_path / "record"
    assert run_e(["mixedcase"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record}).returncode == 0
    assert run_e(["MIXEDCASE"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 1
    assert run_e(["missing.txt"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 1
    assert "--new" in run_e(["missing.txt"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).stderr
    assert run_e(["--new", "missing.txt"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record}).returncode == 0


def test_non_git_search_fallback(tmp_path, fake_proc):
    setup_window(tmp_path, fake_proc)
    (tmp_path / "plain.txt").write_text("x")
    result = run_e(["plain"], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 0
