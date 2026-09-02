from conftest import add_window, make_server, recorded, run_e


def window(tmp_path, fake_proc):
    server = make_server(tmp_path)
    sock = "/run/user/test/vscode-ipc-ext-1.sock"
    add_window(fake_proc, server, 200, sock, True, 20, 201, "/tmp/code-server")
    fake_proc.write()
    return sock


def test_args_and_goto(tmp_path, fake_proc):
    sock = window(tmp_path, fake_proc)
    record = tmp_path / "record"
    (tmp_path / "foo.py").touch()
    result = run_e(["foo.py:12:3"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[0] == (sock.encode(), b"-r", b"-g", b"--", (tmp_path / "foo.py:12:3").as_posix().encode())


def test_new_and_passthrough(tmp_path, fake_proc):
    sock = window(tmp_path, fake_proc)
    record = tmp_path / "record"
    result = run_e(["--new", "new file.txt"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[0] == (sock.encode(), b"-r", b"--", str(tmp_path / "new file.txt").encode())
    weird = tmp_path / "-weird.txt"
    weird.touch()
    result = run_e(["--", "-weird.txt"], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[-1] == (sock.encode(), b"-r", b"--", str(weird).encode())
    assert run_e(["-x"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 2


def test_counts_directory_and_selection(tmp_path, fake_proc):
    window(tmp_path, fake_proc)
    assert run_e([], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 2
    assert run_e(["-d", "a"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 2
    assert "-a" in run_e(["."], tmp_path, {"E_PROC_ROOT": fake_proc.root}).stderr
    assert run_e(["-a", "."], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 0
    assert run_e(["-n", "."], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 0
    assert run_e(["--sock", "99", "x"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).returncode == 2


def test_help_version_dry_run_and_pin(tmp_path, fake_proc):
    sock = window(tmp_path, fake_proc)
    help_result = run_e(["-h"], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert help_result.returncode == 0
    assert "treat a missing path as a new file to create (skip search)" in help_result.stdout
    assert run_e(["--version"], tmp_path, {"E_PROC_ROOT": fake_proc.root}).stdout.strip() == "0.1.0"
    path = tmp_path / "literal"
    path.touch()
    record = tmp_path / "record"
    result = run_e(["--dry-run", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0 and "VSCODE_IPC_HOOK_CLI=" in result.stdout and not record.exists()
    result = run_e(["--sock", sock, str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_TEST_RECORD": record})
    assert result.returncode == 0


def test_forced_terminal_socket_is_used(tmp_path, fake_proc):
    server = make_server(tmp_path)
    ext_sock = "/run/user/test/vscode-ipc-ext-1.sock"
    term_sock = "/run/user/test/vscode-ipc-term-1.sock"
    add_window(fake_proc, server, 200, ext_sock, True, 20, 201, "/tmp/code-server", term_sock)
    fake_proc.write()
    path = tmp_path / "literal"
    path.touch()
    record = tmp_path / "record"
    result = run_e([str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root, "E_VSCODE_IPC_SOCK": term_sock, "E_TEST_RECORD": record})
    assert result.returncode == 0
    assert recorded(record)[0][0] == term_sock.encode()


def test_missing_forced_socket_is_an_argument_error(tmp_path, fake_proc):
    window(tmp_path, fake_proc)
    path = tmp_path / "literal"
    path.touch()
    result = run_e(["--sock", "/run/user/test/vscode-ipc-missing.sock", str(path)], tmp_path, {"E_PROC_ROOT": fake_proc.root})
    assert result.returncode == 2
    assert "socket is not listening" in result.stderr
