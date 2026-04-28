#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# AI Desktop Task Manager — macOS double-click launcher
# ──────────────────────────────────────────────────────────
# 在 macOS Finder 中双击此文件即可启动；首次使用请执行：
#   chmod +x scripts/start.command
# ──────────────────────────────────────────────────────────
cd "$(dirname "$0")"
exec "./start.sh" "$@"
