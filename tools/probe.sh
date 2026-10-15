#!/bin/bash
# probe.sh <标签> <命令...>
#   跑一条命令，完整输出落 logs/probe-<标签>.log，屏幕只回退出码 + 头几行。
#
#   超时默认 30s（PROBE_TIMEOUT 改），stdin 接 /dev/null —— 绝不挂在交互等待上。
#   rc > 128 会标注信号名（137=被 KILL、132=SIGILL、135=SIGSYS…），这类失败要单独看。
cd "$(dirname "$0")/.." || exit 1
label="$1"; shift
[ -n "$label" ] || { echo "usage: probe.sh <label> <cmd...>" >&2; exit 2; }

mkdir -p logs
log="logs/probe-${label}.log"
: > "$log"
timeout "${PROBE_TIMEOUT:-30}" "$@" </dev/null > "$log" 2>&1
rc=$?
printf '== %-22s rc=%-3s ' "$label" "$rc"
if [ "$rc" -gt 128 ]; then printf '[signal %d] ' "$((rc - 128))"; fi
echo "=="
sed -n '1,6p' "$log" | sed 's/^/   /'
if [ -s "$log" ]; then
  n=$(wc -l < "$log"); [ "$n" -gt 6 ] && echo "   ...（共 $n 行，见 $log）"
else
  echo "   （无输出）"
fi
exit "$rc"
