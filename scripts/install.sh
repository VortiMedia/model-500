#!/usr/bin/env bash
# Link each skills/* folder of this repo into ~/.claude/skills/.
#
# Usage:
#   scripts/install.sh              create or repair the links
#   scripts/install.sh --uninstall  remove only the links that point into this repo
#
# You can run it more than once. It never overwrites a real file or folder.
# It exits 1 if it refused anything.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src_root="$repo/skills"
dest_root="$HOME/.claude/skills"

mode="install"
case "${1:-}" in
  "") ;;
  --uninstall) mode="uninstall" ;;
  -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

refused=0

install_one() {
  local src="$1" dest="$2"
  if [ -L "$dest" ]; then
    local now
    now="$(readlink "$dest")"
    if [ "$now" = "$src" ]; then
      echo "ok       $dest"
    elif [[ "$now" == "$src_root"/* ]] && [ ! -e "$dest" ]; then
      ln -sfn "$src" "$dest"
      echo "repaired $dest"
    else
      echo "REFUSED  $dest is a link to $now" >&2
      refused=1
    fi
  elif [ -e "$dest" ]; then
    echo "REFUSED  $dest is a real file or folder" >&2
    refused=1
  else
    ln -s "$src" "$dest"
    echo "linked   $dest -> $src"
  fi
}

uninstall_one() {
  local dest="$1"
  if [ -L "$dest" ]; then
    local now
    now="$(readlink "$dest")"
    if [[ "$now" == "$src_root"/* ]]; then
      rm "$dest"
      echo "removed  $dest"
    else
      echo "skipped  $dest points to $now"
    fi
  elif [ -e "$dest" ]; then
    echo "skipped  $dest is a real file or folder"
  fi
}

if [ "$mode" = "install" ]; then
  mkdir -p "$dest_root"
fi

shopt -s nullglob
found=0
for src in "$src_root"/*/; do
  src="${src%/}"
  [ -f "$src/SKILL.md" ] || continue
  found=1
  dest="$dest_root/$(basename "$src")"
  if [ "$mode" = "install" ]; then
    install_one "$src" "$dest"
  else
    uninstall_one "$dest"
  fi
done

if [ "$found" -eq 0 ]; then
  echo "No skills found in $src_root" >&2
  exit 1
fi

if [ "$refused" -ne 0 ]; then
  echo "Some links were refused. Nothing was overwritten." >&2
  exit 1
fi
