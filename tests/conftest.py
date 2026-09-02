import os
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


class FakeProc:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / "net").mkdir(parents=True)
        self.lines = []
        self.next_inode = 1000

    def _inode(self):
        self.next_inode += 1
        return self.next_inode

    def add_listening(self, path):
        inode = self._inode()
        self.lines.append(("00010000", "01", inode, path))
        return inode

    def add_connected(self, path):
        inode = self._inode()
        self.lines.append(("00000000", "03", inode, path))
        return inode

    def add_proc(self, pid, cmdline, exe, inodes, starttime):
        proc = self.root / str(pid)
        (proc / "fd").mkdir(parents=True)
        (proc / "cmdline").write_bytes(b"\0".join(x.encode() for x in cmdline))
        (proc / "exe").symlink_to(exe)
        fields = [str(pid), "(node)", "S"] + ["0"] * 18 + [str(starttime)]
        (proc / "stat").write_text(" ".join(fields) + "\n")
        for fd, inode in enumerate(inodes, 10):
            (proc / "fd" / str(fd)).symlink_to(f"socket:[{inode}]")

    def write(self):
        lines = ["Num RefCount Protocol Flags Type St Inode Path"]
        for flags, state, inode, path in self.lines:
            lines.append(
                f"0000000000000000: 00000002 00000000 {flags} 0001 {state} {inode} {path}"
            )
        (self.root / "net" / "unix").write_text("\n".join(lines) + "\n")


@pytest.fixture
def fake_proc(tmp_path):
    return FakeProc(tmp_path / "proc")


def make_server(tmp_home, flavor="tunnel", no_cli=False):
    tmp_home = Path(tmp_home)
    if flavor == "tunnel":
        server = tmp_home / ".vscode" / "cli" / "servers" / "Stable-X" / "server"
    else:
        server = tmp_home / ".vscode-server" / "cli" / "servers" / "Stable-X" / "server"
    (server / "bin" / "remote-cli").mkdir(parents=True)
    node = server / "node"
    node.touch()
    node.chmod(0o755)
    if not no_cli:
        code = server / "bin" / "remote-cli" / "code"
        code.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\0' \"$VSCODE_IPC_HOOK_CLI\" \"$@\" >> \"$E_TEST_RECORD\"\n"
            "printf '\\036' >> \"$E_TEST_RECORD\"\n"
            "if [[ ${E_TEST_FAIL_SOCK:-} == \"$VSCODE_IPC_HOOK_CLI\" ]]; then\n"
            "  printf 'Error in request.\\n' >&2; exit 1\n"
            "fi\n"
        )
        code.chmod(0o755)
    return server


def add_window(fp, server, pid, sock, connected, start, srv_pid, srv_sock, term_sock=None):
    srv_inode = fp.add_listening(srv_sock)
    srv_accepted = fp.add_connected(srv_sock)
    terminal_inode = fp.add_listening(term_sock) if term_sock else None
    ext_inode = fp.add_listening(sock)
    ext_accepted = fp.add_connected(srv_sock) if connected else None
    fp.add_proc(srv_pid, ["node", str(server / "out" / "server-main.js"), f"--socket-path={srv_sock}"], server / "node", [srv_inode, srv_accepted] + ([terminal_inode] if terminal_inode else []), start - 1)
    fp.add_proc(pid, ["node", "--type=extensionHost", "--transformURIs"], server / "node", [ext_inode] + ([ext_accepted] if ext_accepted else []), start)


def run_e(args, cwd, env, check=False):
    base = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(Path(cwd)),
        "E_PROC_ROOT": str(env["E_PROC_ROOT"]),
        "E_RUNTIME_DIR": str(env.get("E_RUNTIME_DIR", Path(cwd) / "run")),
        "E_TEST_RECORD": str(env.get("E_TEST_RECORD", Path(cwd) / "records")),
        "E_TIMEOUT": "5",
    }
    base.update({k: str(v) for k, v in env.items()})
    return subprocess.run([str(ROOT / "bin" / "e"), *args], cwd=cwd, env=base, text=True, capture_output=True, check=check)


def recorded(path):
    data = Path(path).read_bytes() if Path(path).exists() else b""
    return [tuple(item.split(b"\0")[:-1]) for item in data.split(b"\036") if item]
