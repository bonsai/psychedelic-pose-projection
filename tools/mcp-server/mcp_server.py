#!/usr/bin/env python3
"""
Psychedelic Pose Projection 用のローカル MCP サーバー（stdio 版）
"""

import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_DIR = Path("/home/bons/bons")

mcp = FastMCP("psychedelic-pose-mcp")


def _run(cmd: list[str], timeout: int = 10, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        lines = []
        if result.stdout:
            lines.append(result.stdout.strip())
        if result.stderr:
            lines.append("[stderr]\n" + result.stderr.strip())
        if result.returncode != 0:
            lines.append(f"[exit code: {result.returncode}]")
        return "\n".join(lines)
    except subprocess.TimeoutExpired:
        return f"[timeout after {timeout}s]"
    except Exception as e:
        return f"[error] {type(e).__name__}: {e}"


@mcp.tool()
def list_project_files() -> list[str]:
    """プロジェクトディレクトリのファイル一覧を返す"""
    files = []
    for item in sorted(PROJECT_DIR.rglob("*")):
        if item.is_file():
            files.append(str(item.relative_to(PROJECT_DIR)))
    return files


@mcp.tool()
def check_camera_status() -> str:
    """WSL2 内のカメラデバイス状態を確認する"""
    outputs = []
    outputs.append("=== /dev/video* ===")
    outputs.append(_run(["bash", "-c", "ls -la /dev/video* 2>&1 || echo 'no video devices'"]))
    outputs.append("=== /proc/version ===")
    outputs.append(_run(["cat", "/proc/version"]))
    outputs.append("=== v4l2-ctl ===")
    outputs.append(_run(["bash", "-c", "v4l2-ctl --list-devices 2>&1 || echo 'v4l2-ctl not installed'"], timeout=5))
    return "\n\n".join(outputs)


@mcp.tool()
def read_file(path: str) -> str:
    """プロジェクト内のテキストファイルを読む"""
    try:
        target = (PROJECT_DIR / path).resolve()
        # プロジェクトディレクトリ外への脱出を防ぐ
        if PROJECT_DIR not in target.parents and target != PROJECT_DIR:
            return "[error] path outside project directory"
        if not target.exists():
            return "[error] file not found"
        if target.stat().st_size > 1_000_000:
            return "[error] file too large (>1MB)"
        return target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[error] {type(e).__name__}: {e}"


@mcp.tool()
def run_standalone_binary() -> str:
    """シングルファイル実行バイナリを短時間起動して状態を確認する"""
    binary = PROJECT_DIR / "psychedelic-pose-projection"
    if not binary.exists():
        return "[error] binary not found"
    return _run([str(binary)], timeout=8, cwd=PROJECT_DIR)


@mcp.tool()
def run_python_sender() -> str:
    """Python OSC sender を短時間起動して状態を確認する"""
    sender = PROJECT_DIR / "processing-osc" / "sender.py"
    if not sender.exists():
        return "[error] sender.py not found"
    python = "/tmp/psychedelic-pose-projection/.venv312/bin/python"
    return _run([python, str(sender)], timeout=8, cwd=PROJECT_DIR)


@mcp.tool()
def get_camera_attach_script() -> str:
    """WSL2 用カメラアタッチ PowerShell スクリプトの内容を返す"""
    script = PROJECT_DIR / "attach-camera.ps1"
    if not script.exists():
        return "[error] attach-camera.ps1 not found"
    return script.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
