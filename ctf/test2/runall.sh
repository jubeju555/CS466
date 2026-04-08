#!/usr/bin/env bash
set -u

# Runs the copied exploit helpers in ./test2.
#
# Default mode is local so you can test every script against every bundled binary.
# Use remote mode when you want to test the four format-string helpers against
# the live services with one shared port.
#
# Usage:
#   ./runall.sh
#   ./runall.sh --mode remote
#   ./runall.sh --mode remote --host example.com --port 32100
#   ./runall.sh --stop-on-flag
#   ./runall.sh --timeout 18

MODE="local"
STOP_ON_FLAG=0
PER_SCRIPT_TIMEOUT=15
HOST="moa6.eecs.utk.edu"
PORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "[!] --mode requires local or remote"
        exit 2
      fi
      MODE="$2"
      shift 2
      ;;
    --stop-on-flag)
      STOP_ON_FLAG=1
      shift
      ;;
    --timeout)
      if [[ $# -lt 2 ]]; then
        echo "[!] --timeout requires a value"
        exit 2
      fi
      PER_SCRIPT_TIMEOUT="$2"
      shift 2
      ;;
    --host)
      if [[ $# -lt 2 ]]; then
        echo "[!] --host requires a value"
        exit 2
      fi
      HOST="$2"
      shift 2
      ;;
    --port)
      if [[ $# -lt 2 ]]; then
        echo "[!] --port requires a value"
        exit 2
      fi
      PORT="$2"
      shift 2
      ;;
    *)
      echo "[!] Unknown option: $1"
      echo "Usage: ./runall.sh [--mode local|remote] [--stop-on-flag] [--timeout SECONDS]"
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CTF_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="python3"
if [[ -x "$CTF_DIR/../.venv/bin/python" ]]; then
  PYTHON_BIN="$CTF_DIR/../.venv/bin/python"
fi

if [[ "$MODE" != "local" && "$MODE" != "remote" ]]; then
  echo "[!] Invalid mode: $MODE"
  exit 2
fi

if [[ "$MODE" == "remote" ]]; then
  if [[ -z "$PORT" ]]; then
    read -r -p "shared port [32100]: " PORT
  fi
  PORT="${PORT:-32100}"
fi

FLAG_REGEX='cosc[0-9-]*-flag-\{[^}]+\}'
FLAG_LOG_FILE="$SCRIPT_DIR/cosc_flags.txt"

if [[ "$MODE" == "local" ]]; then
  : > "$FLAG_LOG_FILE"
fi

LOCAL_SCRIPTS=(
  "fs1.py"
  "fs2.py"
  "fs3.py"
  "fs4.py"
  "fp.py"
  "io.py"
)

LOCAL_BINARIES=(
  "random-game"
  "hidden_string"
  "login"
  "jump"
  "challenge"
  "challenge-io"
)

REMOTE_TASKS=(
  "fs1.py|--mode remote --host $HOST --port $PORT"
  "fs2.py|--mode remote --host $HOST --port $PORT"
  "fs3.py|exploit --remote --host $HOST --port $PORT"
  "fs4.py|--mode remote --host $HOST --port $PORT"
)

run_task() {
  local label="$1"
  local cwd="$2"
  local script="$3"
  shift 3
  local args=("$@")
  local tmp
  tmp="$(mktemp)"

  echo ""
  echo "===== [$label] Running $script ${args[*]} ====="

  (
    cd "$cwd" || exit 1
    timeout "${PER_SCRIPT_TIMEOUT}s" "$PYTHON_BIN" "$script" "${args[@]}"
  ) >"$tmp" 2>&1
  local code=$?

  cat "$tmp"

  if grep -Eiq "$FLAG_REGEX" "$tmp"; then
    local found
    found="$(grep -Eio "$FLAG_REGEX" "$tmp" | head -n1)"
    echo "[+] FLAG DETECTED in $label: $found"
    printf '%s | %s\n' "$label" "$found" >> "$FLAG_LOG_FILE"
    rm -f "$tmp"
    return 10
  fi

  if [[ $code -eq 124 ]]; then
    echo "[!] $label timed out after ${PER_SCRIPT_TIMEOUT}s"
  elif [[ $code -ne 0 ]]; then
    echo "[!] $label exited with code $code"
  fi

  rm -f "$tmp"
  return 0
}

if [[ "$MODE" == "local" ]]; then
  for script in "${LOCAL_SCRIPTS[@]}"; do
    for binary in "${LOCAL_BINARIES[@]}"; do
      label="${script%.py}/${binary}"
      if run_task "$label" "$SCRIPT_DIR" "$script" --mode local --binary "./$binary"; then
        :
      else
        code=$?
        if [[ $code -eq 10 && $STOP_ON_FLAG -eq 1 ]]; then
          echo ""
          echo "[*] Stopping on first flag (exam mode)."
          exit 0
        fi
      fi
    done
  done
else
  : > "$FLAG_LOG_FILE"
  for entry in "${REMOTE_TASKS[@]}"; do
    IFS='|' read -r script args_str <<< "$entry"
    if [[ -n "$args_str" ]]; then
      # shellcheck disable=SC2206
      args=( $args_str )
    else
      args=()
    fi

    if run_task "${script%.py}" "$SCRIPT_DIR" "$script" "${args[@]}"; then
      :
    else
      code=$?
      if [[ $code -eq 10 && $STOP_ON_FLAG -eq 1 ]]; then
        echo ""
        echo "[*] Stopping on first flag (exam mode)."
        exit 0
      fi
    fi
  done
fi

echo ""
if [[ $STOP_ON_FLAG -eq 1 ]]; then
  echo "[*] Finished all scripts. No flag pattern detected."
else
  if [[ "$MODE" == "local" ]]; then
    echo "[*] Finished local matrix runs (--all mode)."
  else
    echo "[*] Finished all remote scripts (--all mode)."
  fi
fi

if [[ -s "$FLAG_LOG_FILE" ]]; then
  echo "[*] Flag log saved to $FLAG_LOG_FILE"
fi
