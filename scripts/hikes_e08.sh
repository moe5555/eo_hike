#!/usr/bin/env bash
# Experiment 08, Stage 1 (notes/08_character_sheet/brief.md): one setting at a time from the h0111 Reference, 1,000 steps from Paris, split streams.
# Tier 1 first (the Reference's seeds 4-7, then taste and decisiveness), then tier 2 (temperament, learning), then tier 3 (memory, capacity, stride, returns).
#
#     scripts/hikes_e08.sh start    # detached, keeps the Mac awake, log in runs/hikes_e08.log, one log per walk in runs/e08_logs/
#     scripts/hikes_e08.sh stop     # stops the batch and every walk it started
#
# Three walkers side by side with three threads each (four pushed this 16 GB machine further into swap). Walks that have finished are
# not repeated. A watchdog stops the whole batch, running walks included, if the disk has under MIN_FREE_GB left or if .git/objects grows
# by MAX_GIT_GROWTH_MB: on 2026-11-01 something kept trying to store an untracked film in .git until the disk was full.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=3 MKL_NUM_THREADS=3
MIN_FREE_GB=10
MAX_GIT_GROWTH_MB=1000
PIDFILE=runs/e08_batch.pgid
LOG=runs/hikes_e08.log

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
    mkdir -p runs/e08_logs
    # a session of its own, so that closing the editor doesn't end the walks and the stop command reaches all of them
    nohup .venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' caffeinate -i "$0" run >> "$LOG" 2>&1 < /dev/null &
    echo "started; stop with: scripts/hikes_e08.sh stop"
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
  # a walk stopped halfway cannot resume: move its folder aside rather than walk again on top of its files
  if [ -d "runs/${c}_s${s}" ]; then
    mkdir -p runs/e08_partial
    mv "runs/${c}_s${s}" "runs/e08_partial/${c}_s${s}_$(date '+%Y%m%d_%H%M%S')"
    echo "=== moved partial ${c}_s${s} to runs/e08_partial/"
  fi
  echo "=== $(date '+%F %T') start ${c}_s${s}"
  if .venv/bin/python -m agent.walk "configs/08_character_sheet/${c}.yaml" --seed "$s" > "runs/e08_logs/${c}_s${s}.log" 2>&1; then
    tail -n 1 "runs/e08_logs/${c}_s${s}.log"
  else
    echo "=== FAILED: ${c}_s${s}"
  fi
}
export -f walk
{
  for s in 4 5 6 7; do echo "e08_reference $s"; done
  # tier 1
  for c in e08_novelty_only e08_progress_only e08_surprise e08_knn_3 e08_knn_30 e08_ema_005 e08_ema_08 e08_temp_02 e08_temp_10 e08_crop_32 e08_crop_128; do
    for s in 0 1 2 3; do echo "$c $s"; done
  done
  # tier 2
  for c in e08_patience_08 e08_farjump_0 e08_farjump_02 e08_update_1 e08_update_12 e08_null_patience_03; do
    for s in 0 1 2 3; do echo "$c $s"; done
  done
  # tier 3; capacity seeds 1-3 only, s0 is h0111_eye_half_s0 and h0111_eye_double_s0
  for c in e08_buffer_512 e08_buffer_8192 e08_returncost_05 e08_nobackstep e08_radius_25; do
    for s in 0 1 2 3; do echo "$c $s"; done
  done
  for c in e08_width_05 e08_width_2; do
    for s in 1 2 3; do echo "$c $s"; done
  done
} | xargs -P 3 -L 1 bash -c 'walk "$0" "$1"'
kill "$watchdog" 2>/dev/null
rm -f "$PIDFILE"
echo "=== $(date '+%F %T') all done"
