from pathlib import Path

from conftest import add_window, make_server, recorded, run_e


def test_tunnel_ext_host_happy_path(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-ext-1.sock"
    add_window(fake_proc, server, 200, sock, True, 20, 201, "/tmp/code-server", "/run/user/test/vscode-ipc-term-1.sock")
    fake_proc.write()
    record = tmp_path / "record"
    path = tmp_path / "hello.py"
    path.write_text("x")
    result = run_e([str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[0] == (sock.encode(), b"-r", b"--", str(path).encode())


def test_stale_and_unowned_sockets_are_ignored(tmp_path, fake_proc):
    server = make_server(tmp_path)
    live = "/run/user/test/vscode-ipc-live-1.sock"
    add_window(fake_proc, server, 200, live, True, 20, 201, "/tmp/code-server")
    fake_proc.add_listening("/run/user/test/vscode-ipc-unowned-1.sock")
    fake_proc.write()
    (tmp_path / "stale.sock").touch()
    result = run_e(["--list"], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 0
    assert live in result.stdout
    assert "/run/user/test/vscode-ipc-unowned-1.sock" not in result.stdout


def test_tunnel_preferred_and_disconnected_tunnel_loses(tmp_path, fake_proc):
    tunnel = make_server(tmp_path / "t", "tunnel")
    ssh = make_server(tmp_path / "s", "remote")
    add_window(fake_proc, tunnel, 200, "/run/user/test/vscode-ipc-t-1.sock", False, 20, 201, "/tmp/code-t")
    add_window(fake_proc, ssh, 300, "/run/user/test/vscode-ipc-s-1.sock", True, 10, 301, "/tmp/code-s")
    fake_proc.write()
    result = run_e(["--list"], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 0
    rows = result.stdout.splitlines()
    assert "remote-ssh" in rows[1]


def test_connected_window_and_exthost_rank_first(tmp_path, fake_proc):
    one = make_server(tmp_path / "one")
    two = make_server(tmp_path / "two")
    add_window(fake_proc, one, 200, "/run/user/test/vscode-ipc-one-1.sock", True, 10, 201, "/tmp/code-one", "/run/user/test/vscode-ipc-term-1.sock")
    add_window(fake_proc, two, 300, "/run/user/test/vscode-ipc-two-1.sock", True, 20, 301, "/tmp/code-two")
    fake_proc.write()
    path = tmp_path / "f"
    path.touch()
    result = run_e(["--dry-run", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 0
    assert "vscode-ipc-two-1.sock" in result.stdout


def test_disconnected_candidate_is_used_with_warning(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-ext-1.sock"
    add_window(fake_proc, server, 200, sock, False, 20, 201, "/tmp/code-server")
    fake_proc.write()
    path = tmp_path / "f"
    path.touch()
    record = tmp_path / "record"
    result = run_e([str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert "disconnected" in result.stderr


def test_failed_top_endpoint_falls_through_to_second(tmp_path, fake_proc):
    first_server = make_server(tmp_path / "first")
    second_server = make_server(tmp_path / "second")
    first = "/run/user/test/vscode-ipc-first.sock"
    second = "/run/user/test/vscode-ipc-second.sock"
    add_window(fake_proc, first_server, 200, first, True, 20, 201, "/tmp/code-first")
    add_window(fake_proc, second_server, 300, second, True, 10, 301, "/tmp/code-second")
    fake_proc.write()
    record = tmp_path / "record"
    path = tmp_path / "f"
    path.touch()
    result = run_e([str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record, "E_TEST_FAIL_SOCK": first})
    assert result.returncode == 0
    assert [row[0] for row in recorded(record)] == [first.encode(), second.encode()]


def test_single_failed_endpoint_mentions_verbose_diagnostics(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-only.sock"
    add_window(fake_proc, server, 200, sock, True, 20, 201, "/tmp/code-server")
    fake_proc.write()
    path = tmp_path / "f"
    path.touch()
    result = run_e([str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": tmp_path / "record", "E_TEST_FAIL_SOCK": sock})
    assert result.returncode == 1
    assert "rerun with -v" in result.stderr


def test_all_sends_once_per_connected_process(tmp_path, fake_proc):
    first_server = make_server(tmp_path / "first")
    second_server = make_server(tmp_path / "second")
    first = "/run/user/test/vscode-ipc-first.sock"
    second = "/run/user/test/vscode-ipc-second.sock"
    add_window(fake_proc, first_server, 200, first, True, 20, 201, "/tmp/code-first")
    add_window(fake_proc, second_server, 300, second, True, 10, 301, "/tmp/code-second")
    fake_proc.write()
    record = tmp_path / "record"
    path = tmp_path / "f"
    path.touch()
    result = run_e(["--all", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert {row[0] for row in recorded(record)} == {first.encode(), second.encode()}
    assert len(recorded(record)) == 2


def test_all_skips_disconnected_processes(tmp_path, fake_proc):
    connected_server = make_server(tmp_path / "connected")
    disconnected_server = make_server(tmp_path / "disconnected")
    connected = "/run/user/test/vscode-ipc-connected.sock"
    disconnected = "/run/user/test/vscode-ipc-disconnected.sock"
    add_window(fake_proc, connected_server, 200, connected, True, 20, 201, "/tmp/code-connected")
    add_window(fake_proc, disconnected_server, 300, disconnected, False, 10, 301, "/tmp/code-disconnected")
    fake_proc.write()
    record = tmp_path / "record"
    path = tmp_path / "f"
    path.touch()
    result = run_e(["--all", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record) == [(connected.encode(), b"-r", b"--", str(path).encode())]


def test_all_rejects_when_every_process_is_disconnected(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-disconnected.sock"
    add_window(fake_proc, server, 200, sock, False, 20, 201, "/tmp/code-server")
    fake_proc.write()
    path = tmp_path / "f"
    path.touch()
    result = run_e(["--all", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 1
    assert "--all found no connected window (all 1 candidate(s) look disconnected); use --sock to force one" in result.stderr


def test_bad_server_and_bash_false_positive(tmp_path, fake_proc):
    server = make_server(tmp_path, no_cli=True)
    add_window(fake_proc, server, 200, "/run/user/test/vscode-ipc-ext-1.sock", True, 20, 201, "/tmp/code-server")
    fake_proc.add_proc(400, ["bash", "--type=extensionHost"], "/usr/bin/bash", [], 99)
    fake_proc.write()
    result = run_e(["--list"], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 1
    assert "no live VS Code window" in result.stderr
