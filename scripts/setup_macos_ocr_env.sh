#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-ocr311"

PYTHON_BIN=""
if [[ -x "/opt/homebrew/bin/python3.11" ]]; then
  PYTHON_BIN="/opt/homebrew/bin/python3.11"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.11)"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "未找到 Python 3.11。请先安装 python3.11（推荐 Homebrew 版本）后再运行。"
  exit 1
fi

echo "使用解释器: ${PYTHON_BIN}"

if [[ ! -d "${VENV_DIR}" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements.txt" -r "${ROOT_DIR}/requirements-ocr.txt"

echo
echo "OCR 环境已准备完成。"
echo "激活命令:"
echo "  source .venv-ocr311/bin/activate"
echo
echo "启动应用:"
echo "  python src/main.py"
