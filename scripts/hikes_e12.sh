#!/usr/bin/env bash
# Experiment 12 (notes/12_two_eye/, brief notes/brief_landsat_pipeline.md E14): the short factorial of the two-eye walker on the e10
# pass world in sqrt tone, 1,000 steps, seeds 0-1, plus the two replayed-schedule controls. `start smoke` walks the mission-world smoke
# walk (E16, 500 steps).
#
#     scripts/hikes_e12.sh start factorial   # detached, keeps the Mac awake, log in runs/hikes_e12.log, one log per walk in runs/e12_logs/
#     scripts/hikes_e12.sh stop
#
# As scripts/hikes_e09.sh: three walkers side by side with three threads each; finished walks are not repeated; a watchdog stops the
# batch if the disk has under MIN_FREE_GB left or .git/objects grows by MAX_GIT_GROWTH_MB.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=3 MKL_NUM_THREADS=3
MIN_FREE_GB=10
MAX_GIT_GROWTH_MB=1000
PIDFILE=runs/e12_batch.pgid
LOG=runs/hikes_e12.log

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
    mkdir -p runs/e12_logs
    case "${2:-}" in factorial|smoke) ;; *) echo "usage: $0 start factorial|smoke"; exit 2 ;; esac
    nohup .venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' caffeinate -i "$0" run "$2" >> "$LOG" 2>&1 < /dev/null &
    echo "started; stop with: scripts/hikes_e12.sh stop"
    exit 0 ;;
  stop) stop_batch "stop command"; exit 0 ;;
  run) ;;
  *) echo "usage: $0 start <stage> | stop"; exit 2 ;;
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
  local c=$1 s=$2 extra=${3:-}
  [ -f "runs/${c}_s${s}/final.pt" ] && { echo "=== have ${c}_s${s}"; return; }
  if [ -d "runs/${c}_s${s}" ]; then
    mkdir -p runs/e12_partial
    mv "runs/${c}_s${s}" "runs/e12_partial/${c}_s${s}_$(date '+%Y%m%d_%H%M%S')"
    echo "=== moved partial ${c}_s${s} to runs/e12_partial/"
  fi
  echo "=== $(date '+%F %T') start ${c}_s${s}"
  if .venv/bin/python -m agent.walk "configs/12_two_eye/${c}.yaml" --seed "$s" $extra > "runs/e12_logs/${c}_s${s}.log" 2>&1; then
    tail -n 1 "runs/e12_logs/${c}_s${s}.log"
  else
    echo "=== FAILED: ${c}_s${s}"
  fi
}
export -f walk
echo "=== $(date '+%F %T') stage ${2}, $(free_gb) GB free"
if [ "$2" = factorial ]; then
  jobs_list=""
  for s in 0 1; do
    for c in e12_v1 e12_null e12_grid_mean e12_grid_top4 e12_grid_top1 e12_two_top4 e12_two_top4_g2 e12_two_top4_shifted e12_two_top4_shuffled; do
      jobs_list+="$c $s"$'\n'
    done
  done
  printf '%s' "$jobs_list" | xargs -P 3 -L 1 bash -c 'walk "$0" "$1"'
else
  walk e12_mission_smoke 0
fi
echo "=== $(date '+%F %T') stage ${2} done, $(free_gb) GB free"
kill "$watchdog" 2>/dev/null
rm -f "$PIDFILE"
