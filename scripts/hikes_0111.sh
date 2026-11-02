#!/usr/bin/env bash
# Round h0111 (notes/brief_0111.md): null walker, teleport landing variants and eye sizes, 1,000 steps from Paris, split streams.
#
#     scripts/hikes_0111.sh start    # detached, keeps the Mac awake, log in runs/hikes_0111.log, one log per walk in runs/h0111_logs/
#     scripts/hikes_0111.sh stop     # stops the batch and every walk it started
#
# Three walkers side by side with three threads each (four pushed this 16 GB machine further into swap). Walks that have finished are
# not repeated. A watchdog stops the whole batch, running walks included, if the disk has under MIN_FREE_GB left or if .git/objects grows
# by MAX_GIT_GROWTH_MB: on 2026-11-01 something kept trying to store an untracked film in .git until the disk was full.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=3 MKL_NUM_THREADS=3
MIN_FREE_GB=10
MAX_GIT_GROWTH_MB=1000
PIDFILE=runs/h0111_batch.pgid
LOG=runs/hikes_0111.log

stop_batch() {
  [ -f "$PIDFILE" ] || { echo "no batch running"; return 0; }
  local pg
  pg=$(cat "$PIDFILE")
  rm -f "$PIDFILE"
  echo "=== $(date '+%F %T') stopping batch ($1)" >> "$LOG"
  kill -TERM -- "-$pg" 2>/dev/null
}

case "${1:-}" in
  start)
    [ -f "$PIDFILE" ] && { echo "already running, group $(cat "$PIDFILE")"; exit 1; }
    mkdir -p runs/h0111_logs
    # a session of its own, so that closing the editor doesn't end the walks and the stop command reaches all of them
    nohup .venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' caffeinate -i "$0" run >> "$LOG" 2>&1 < /dev/null &
    echo "started; stop with: scripts/hikes_0111.sh stop"
    exit 0 ;;
  stop) stop_batch "stop command"; exit 0 ;;
  run) ;;
  *) echo "usage: $0 start | stop"; exit 2 ;;
esac

ps -o pgid= -p $$ | tr -d ' ' > "$PIDFILE"

git_mb() { du -sm .git/objects | cut -f1; }
free_gb() { df -g . | awk 'NR==2 {print $4}'; }
if [ "$(free_gb)" -lt "$MIN_FREE_GB" ]; then stop_batch "only $(free_gb) GB free at the start"; exit 1; fi
(
  base=$(git_mb)
  while sleep 30; do
    free=$(free_gb) git=$(git_mb)
    if [ "$free" -lt "$MIN_FREE_GB" ]; then stop_batch "only ${free} GB free"; fi
    if [ $((git - base)) -gt "$MAX_GIT_GROWTH_MB" ]; then stop_batch ".git/objects grew from ${base} to ${git} MB"; fi
  done
) &
watchdog=$!

walk() {
  local c=$1 s=$2
  [ -f "runs/${c}_s${s}/final.pt" ] && { echo "=== have ${c}_s${s}"; return; }
  echo "=== $(date '+%F %T') start ${c}_s${s}"
  if .venv/bin/python -m agent.walk "configs/${c}.yaml" --seed "$s" > "runs/h0111_logs/${c}_s${s}.log" 2>&1; then
    tail -n 1 "runs/h0111_logs/${c}_s${s}.log"
  else
    echo "=== FAILED: ${c}_s${s}"
  fi
}
export -f walk
{
  for c in h0111_reference h0111_null h0111_bored h0111_reference_k3 h0111_bored_k3 h0111_reference_k8 h0111_bored_k8; do
    for s in 0 1 2 3; do echo "$c $s"; done
  done
} | xargs -P 3 -L 1 bash -c 'walk "$0" "$1"'
# eye size last and on its own: the current size is h0111_reference_s0
for c in h0111_eye_half h0111_eye_double; do walk "$c" 0; done
kill "$watchdog" 2>/dev/null
rm -f "$PIDFILE"
echo "=== $(date '+%F %T') all done"
