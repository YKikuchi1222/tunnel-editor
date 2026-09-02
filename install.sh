#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target_dir=${HOME}/.local/bin
target=$target_dir/e
source=$repo_dir/bin/e

case ${1:-} in
    --check)
        if [[ -L $target && $(readlink "$target") == "$source" ]]; then
            printf 'e: installed: %s -> %s\n' "$target" "$source"
            exit 0
        fi
        printf 'e: not installed at %s\n' "$target"
        exit 1
        ;;
    --uninstall)
        if [[ -L $target ]]; then
            link=$(readlink "$target")
            if [[ $link == "$source" ]]; then
                rm -- "$target"
                printf 'e: removed %s\n' "$target"
            else
                printf 'e: refusing to remove unrelated symlink %s -> %s\n' "$target" "$link" >&2
                exit 2
            fi
        else
            printf 'e: nothing to uninstall at %s\n' "$target"
        fi
        ;;
    '')
        mkdir -p -- "$target_dir"
        if [[ -e $target && ! -L $target ]]; then
            printf 'e: refusing to overwrite non-symlink %s\n' "$target" >&2
            exit 2
        fi
        ln -sfn -- "$source" "$target"
        printf 'e: installed: %s -> %s\n' "$target" "$source"
        ;;
    *)
        printf 'Usage: %s [--check|--uninstall]\n' "${BASH_SOURCE[0]}" >&2
        exit 2
        ;;
esac
