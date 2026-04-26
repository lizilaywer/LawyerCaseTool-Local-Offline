# -*- coding: utf-8 -*-
"""Windows 启动与运行性能采集脚本。

用法：
    python scripts/windows_perf_probe.py --runs 5
    python scripts/windows_perf_probe.py --python .venv\\Scripts\\python.exe --runs 5
"""

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_PREFIX = "LEXORA_BENCHMARK "


def _read_process_memory_bytes(pid: int) -> Optional[int]:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        process_vm_read = 0x0010

        class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t),
            ]

        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information | process_vm_read,
            False,
            pid,
        )
        if not handle:
            return None
        try:
            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle,
                ctypes.byref(counters),
                counters.cb,
            )
            return int(counters.WorkingSetSize) if ok else None
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        return None


def run_once(python_exe: str, exit_ms: int) -> Dict[str, object]:
    cmd = [
        python_exe,
        str(PROJECT_ROOT / "src" / "main.py"),
        "--benchmark-startup",
        "--benchmark-exit-ms",
        str(exit_ms),
    ]
    start = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    peak_memory = 0
    stdout_lines: List[str] = []
    while proc.poll() is None:
        memory = _read_process_memory_bytes(proc.pid)
        if memory:
            peak_memory = max(peak_memory, memory)
        time.sleep(0.05)

    stdout, stderr = proc.communicate(timeout=5)
    stdout_lines.extend(stdout.splitlines())
    elapsed_ms = (time.perf_counter() - start) * 1000

    metrics = {}
    for line in stdout_lines:
        if line.startswith(BENCHMARK_PREFIX):
            metrics = json.loads(line[len(BENCHMARK_PREFIX):])
            break
    if not metrics:
        raise RuntimeError(f"没有收到性能输出。stderr:\n{stderr}")

    metrics["process_elapsed_ms"] = round(elapsed_ms, 2)
    metrics["peak_working_set_mb"] = round(peak_memory / 1024 / 1024, 2) if peak_memory else None
    metrics["return_code"] = proc.returncode
    return metrics


def summarize(values: List[Dict[str, object]]) -> Dict[str, object]:
    keys = [
        "startup_ms",
        "process_elapsed_ms",
        "memory_rss_mb",
        "peak_working_set_mb",
        "event_loop_tick_hz",
        "frame_tick_hz",
    ]
    summary = {"runs": len(values)}
    for key in keys:
        numeric = [float(item[key]) for item in values if isinstance(item.get(key), (int, float))]
        if not numeric:
            continue
        summary[key] = {
            "min": round(min(numeric), 2),
            "mean": round(statistics.mean(numeric), 2),
            "max": round(max(numeric), 2),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="LEXORA Windows 性能采集")
    parser.add_argument("--python", default=sys.executable, help="Python 解释器路径")
    parser.add_argument("--runs", type=int, default=5, help="采集次数")
    parser.add_argument("--exit-ms", type=int, default=1200, help="窗口显示后退出延迟")
    parser.add_argument("--json-out", default="", help="保存 JSON 报告路径")
    args = parser.parse_args()

    results = [run_once(args.python, args.exit_ms) for _ in range(max(1, args.runs))]
    report = {
        "platform": sys.platform,
        "python": args.python,
        "runs": results,
        "summary": summarize(results),
    }

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
