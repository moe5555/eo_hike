#!/usr/bin/env bash
# Experiment 09 (notes/09_compass/brief_e09_compass.md): the compass walker, 1,000 steps from Paris.
# The queue is one stage at a time: `start 1` walks Stage 1 (calibration of radius_delta, 12 walks); `start 1b` walks it again with the
# drive's averages at 20 / 200 steps (Stage 1 report, finding 17); `start 1c` walks the compass Reference (e09_ref) on seeds 0-7;
# `start 2` writes the control schedules from it and walks Stage 2 (48 walks); `start 3a` walks the larger eye (crop_px 128 and 192, seeds
# 0-3), writes their shifted schedules, then walks those controls (16 walks in all).
#
#     scripts/hikes_e09.sh start 1  # Stage 1, detached, keeps the Mac awake, log in runs/hikes_e09.log, one log per walk in runs/e09_logs/
#     scripts/hikes_e09.sh stop     # stops the batch and every walk it started
#
# Three walkers side by side with three threads each (four pushed this 16 GB machine further into swap). Walks that have finished are
# not repeated. A watchdog stops the whole batch, running walks included, if the disk has under MIN_FREE_GB left or if .git/objects grows
# by MAX_GIT_GROWTH_MB: on 2026-11-01 something kept trying to store an untracked film in .git until the disk was full.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=3 MKL_NUM_THREADS=3
MIN_FREE_GB=10
MAX_GIT_GROWTH_MB=1000
PIDFILE=runs/e09_batch.pgid
LOG=runs/hikes_e09.log

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
    mkdir -p runs/e09_logs
    # a session of its own, so that closing the editor doesn't end the walks and the stop command reaches all of them
    case "${2:-}" in 1|1b|1c|2|3a) ;; *) echo "usage: $0 start 1|1b|1c|2|3a"; exit 2 ;; esac
    nohup .venv/bin/python -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])' caffeinate -i "$0" run "$2" >> "$LOG" 2>&1 < /dev/null &
    echo "started; stop with: scripts/hikes_e09.sh stop"
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
  local c=$1 s=$2
  [ -f "runs/${c}_s${s}/final.pt" ] && { echo "=== have ${c}_s${s}"; return; }
  # a walk stopped halfway cannot resume: move its folder aside rather than walk again on top of its files
  if [ -d "runs/${c}_s${s}" ]; then
    mkdir -p runs/e09_partial
    mv "runs/${c}_s${s}" "runs/e09_partial/${c}_s${s}_$(date '+%Y%m%d_%H%M%S')"
    echo "=== moved partial ${c}_s${s} to runs/e09_partial/"
  fi
  echo "=== $(date '+%F %T') start ${c}_s${s}"
  if .venv/bin/python -m agent.walk "configs/09_compass/${c}.yaml" --seed "$s" > "runs/e09_logs/${c}_s${s}.log" 2>&1; then
    tail -n 1 "runs/e09_logs/${c}_s${s}.log"
  else
    echo "=== FAILED: ${c}_s${s}"
  fi
}
export -f walk
echo "=== $(date '+%F %T') stage ${2}, $(free_gb) GB free"
if [ "$2" = 2 ]; then
  .venv/bin/python analysis/e09/schedules.py controls --reference e09_ref >> "$LOG" 2>&1 || { stop_batch "schedules failed"; exit 1; }
fi
queue() {
  case "$1" in
    1)  # Stage 1: radius_delta at the Stage 0 choice (0.35), half and double; seeds 0-3, the seed first so that all three deltas run side by side
      for s in 0 1 2 3; do for c in e09_reference e09_delta_0175 e09_delta_07; do echo "$c $s"; done; done ;;
    1b)  # Stage 1 again (round 2): the drive's averages at 20 / 200 steps, radius_delta 0.25, 0.35, 0.5; seeds 0-3, the seed first
      for s in 0 1 2 3; do for c in e09_avg20_d035 e09_avg20_d025 e09_avg20_d05; do echo "$c $s"; done; done ;;
    1c)  # the compass Reference (e09_ref: Δ 0.25, averages 20 / 200, drive from step 50), seeds 0-7: the check on 0-3, and Stage 2's 4-7
      for s in 0 1 2 3 4 5 6 7; do echo "e09_ref $s"; done ;;
    2)  # Stage 2: the Null, the three radius controls and local only on seeds 0-7, starts B and C on 0-3; seeds 0-3 first.
        # The controls replay the Reference walk of the same seed (schedules written just before, below).
      for s in 0 1 2 3; do for c in e09_null e09_shifted e09_shuffled e09_fixed e09_local e09_ref_startb e09_ref_startc; do echo "$c $s"; done; done
      for s in 4 5 6 7; do for c in e09_null e09_shifted e09_shuffled e09_fixed e09_local; do echo "$c $s"; done; done ;;
    3a)  # Stage 3, the larger eye: crop_px 128 and 192 on seeds 0-3, seed first
      for s in 0 1 2 3; do for c in e09_crop128 e09_crop192; do echo "$c $s"; done; done ;;
    3a_shifted)  # their shifted controls, from the schedules written between the two queues
      for s in 0 1 2 3; do for c in e09_crop128_shifted e09_crop192_shifted; do echo "$c $s"; done; done ;;
  esac
}
queue "$2" | xargs -P 3 -L 1 bash -c 'walk "$0" "$1"'
if [ "$2" = 3a ] && [ -f "$PIDFILE" ]; then
  for px in 128 192; do
    .venv/bin/python analysis/e09/schedules.py controls --reference "e09_crop${px}" --seeds 0-3 --prefix "crop${px}_" >> "$LOG" 2>&1 || { stop_batch "schedules failed"; exit 1; }
  done
  queue 3a_shifted | xargs -P 3 -L 1 bash -c 'walk "$0" "$1"'
fi
kill "$watchdog" 2>/dev/null
rm -f "$PIDFILE"
echo "=== $(date '+%F %T') all done"
