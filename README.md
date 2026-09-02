# "e" A File Opener for Code Tunnel

`e` opens a file in the VS Code window connected to this machine through `code tunnel`:

```text
e path/to/file.py
e path/to/file.py:42:3
e --new path-that-does-not-exist.txt
e -d left.txt right.txt
```

The default is `--reuse-window` (`-r`). Use `-n` for a new window, `-a` to add a
folder to the current workspace, `-w` to wait, and `--` before a filename that
starts with `-`. `e --list` shows the endpoints it can see; `e --dry-run FILE`
prints the exact remote CLI command without opening anything. `--gc` is an
explicit opt-in cleanup of stale `vscode-ipc-*.sock` files in the runtime
directory; `--gc --dry-run` lists what would be removed.

## Discovery and ranking

Each invocation reads `/proc/net/unix`, then inspects only same-user processes
whose command lines look like a VS Code extension host or server-main process.
It derives the server root from `/proc/PID/exe` and requires that server's
`bin/remote-cli/code`; no cache or resident process is used. Listener ownership
and accepted connections are inferred from socket inodes and process file
descriptors, so stale socket files are ignored.

Records are ranked by connected status, tunnel before Remote-SSH, extension
host before integrated-terminal CLI servers, process start time, and socket
inode. A disconnected extension host is still attempted because VS Code can
replay the request during its reconnection grace period. Use `-v` for reasons
why candidate processes were skipped.

`--list` prints the columns `RANK CONN FLAVOR TIER PID SOCKET SERVER_ROOT`.
`CONN` is `yes` when the extension host holds an accepted connection on the
server-main listener, `no` when the process is alive but its window is
disconnected within the reconnection grace period, and `?` when no server-main
listener is visible. `--sock N` selects a ranked endpoint; `--sock PATH`
selects a listening socket path. `E_VSCODE_IPC_SOCK` provides the same path or
rank pinning through the environment. `--all` sends the request once to every
connected window.

## Path search

Existing paths are passed literally. Missing names are searched only when
needed: tracked/untracked-but-not-ignored files from the current git subtree
are preferred, followed by `rg --files`, then a bounded `find` fallback.
Patterns are extended regular expressions with smart case matching. Ambiguous
results are listed and require an interactive choice; non-interactive use
returns an error. `--new` skips searching and lets VS Code create the path on
save. Search is capped by `E_SEARCH_MAX` (200 by default). Search mode does not
support newlines in file names.

Exit status is 0 for a successful request (or informational command), 1 when
no endpoint can handle the request or search is unsuccessful, and 2 for an
invalid command line or selection.

## Installation

From this repository:

```bash
./install.sh
./install.sh --check
./install.sh --uninstall
```

Installation creates `~/.local/bin/e` as a symlink and refuses to overwrite a
non-symlink.

## Environment variables

`E_PROC_ROOT` points discovery at an alternate proc tree for tests. `E_VSCODE_IPC_SOCK`
pins a listening IPC socket. `E_RUNTIME_DIR` controls the directory used only
by `--gc`; otherwise `XDG_RUNTIME_DIR`, `TMPDIR`, or `/tmp` is used. `E_TIMEOUT`
sets the request timeout in seconds (not for `-w`), `E_SEARCH_MAX` caps search
results, and `E_DEBUG` enables verbose diagnostics. `LC_ALL=C` is set internally
for stable parsing.

## Limitations and future work

The tool assumes the VS Code CLI/server layout described above and selects by
connection state rather than workspace identity. A future version could use a
direct `curl --unix-socket` transport (about 30 ms), a validated short-lived
socket cache, workspace-aware window selection, and optional `fzf` integration.
