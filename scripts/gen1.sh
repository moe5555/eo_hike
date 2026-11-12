#!/usr/bin/env bash
# Brief v2 (notes/brief_landsat_v2_run.md): the dry runs (Gate B, section 6) on the clock world of Landsat 1.
#
#     scripts/gen1.sh start dryrun     # curious and Null, start cells 0-2, interleaved, until the clock ends them or 3,000 steps
#     scripts/gen1.sh start long       # Moe 2026-11-13: one more curious walk (start cell 3) until the clock ends it or 20,000 tiles
#     scripts/gen1.sh stop
#
# Detached, keeps the Mac awake; log runs/gen1_batch.log, one log per walk in runs/<phase>/logs/. PARALLEL walkers side by side (2) with
# three threads each, in the order curious 0, Null 0, curious 1, ... A finished walk (walk.json) is not repeated; an unfinished one with a
# checkpoint is resumed. Beside the walkers: the cache cap (data/cache_cap.py, LRU, CAP_GB) and a watchdog that stops the batch if the
# disk has under MIN_FREE_GB left or .git/objects grows by MAX_GIT_GROWTH_MB. Generation 1 (section 7) waits for Moe's approval at Gate B.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=3 MKL_NUM_THREADS=3
MIN_FREE_GB=5
MAX_GIT_GROWTH_MB=1000
CAP_GB=${CAP_GB:-12}
PARALLEL=${PARALLEL:-2}  # walkers side by side: three swapped on the 16 GB Mac (each holds ~2 GB: the world index, its BallTree, tiles)
PIDFILE=runs/gen1_batch.pgid
LOG=runs/gen1_batch.log

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
    case "${2:-}" in dryrun|long) ;; *) echo "usage: $0 start dryrun|long"; exit 2 ;; esac
    mkdir -p runs
    nohup .venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' caffeinate -i "$0" run "$2" >> "$LOG" 2>&1 < /dev/null &
    echo "started; stop with: scripts/gen1.sh stop"
    exit 0 ;;
  stop) stop_batch "stop command"; exit 0 ;;
  run) ;;
  *) echo "usage: $0 start <phase> | stop"; exit 2 ;;
esac

phase=$2
ps -o pgid= -p $$ | tr -d ' ' > "$PIDFILE"
git_mb() { du -sm .git/objects | cut -f1; }
free_gb() { df -g . | awk 'NR==2 {print $4}'; }
if [ "$(free_gb)" -lt "$MIN_FREE_GB" ]; then stop_batch "only $(free_gb) GB free at the start"; exit 1; fi
.venv/bin/python data/cache_cap.py --cap-gb "$CAP_GB" --every 60 >> runs/${phase}_cache_cap.log 2>&1 &
cap_pid=$!
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
  local cond=$1 k=$2 phase=$3 steps=$4 tiles=${5:-}
  local dir
  dir=runs/${phase}/${cond}/w$(printf '%03d' "$k")
  [ -f "$dir/walk.json" ] && { echo "=== have ${cond} w${k}"; return; }
  local extra=""
  [ -f "$dir/resume.pt" ] && extra="--resume"
  [ -n "$tiles" ] && extra="$extra --tile-cap $tiles"
  mkdir -p "runs/${phase}/logs"
  echo "=== $(date '+%F %T') start ${cond} w${k} ${extra}"
  if .venv/bin/python -m agent.walk "configs/gen1/${cond}.yaml" --walk "$k" --phase "$phase" --steps "$steps" $extra >> "runs/${phase}/logs/${cond}_w${k}.log" 2>&1; then
    tail -n 1 "runs/${phase}/logs/${cond}_w${k}.log"
  else
    echo "=== FAILED: ${cond} w${k}"
  fi
}
export -f walk
echo "=== $(date '+%F %T') phase ${phase}, $(free_gb) GB free, cache cap ${CAP_GB} GB, ${PARALLEL} side by side"
jobs_list=""
case "$phase" in
  dryrun) for k in 0 1 2; do for c in curious null; do jobs_list+="$c $k dryrun 3000"$'\n'; done; done ;;
  long) jobs_list+="curious 3 long 40000 20000"$'\n' ;;
esac
printf '%s' "$jobs_list" | xargs -P "$PARALLEL" -L 1 bash -c 'walk "$0" "$1" "$2" "$3" "$4"'
echo "=== $(date '+%F %T') phase ${phase} done, $(free_gb) GB free"
kill "$watchdog" "$cap_pid" 2>/dev/null
rm -f "$PIDFILE"
