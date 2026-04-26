#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-ocr311"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "未找到 .venv-ocr311，请先运行 scripts/setup_macos_ocr_env.sh"
  exit 1
fi

cd "${ROOT_DIR}"
exec "${VENV_DIR}/bin/python" src/main.py "$@"
