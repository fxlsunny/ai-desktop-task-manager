#!/usr/bin/env bash
# Convenience launcher — forwards to scripts/start.sh
# 便捷入口：等价于运行 ./scripts/start.sh
cd "$(dirname "$0")"
exec "./scripts/start.sh" "$@"
