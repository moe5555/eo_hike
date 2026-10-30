#!/usr/bin/env bash
# Hikes 29.10 (notes/hikes_2910/): four characters x 2 seeds + the reference's seed 1, 1,000 steps each, Mac CPU.
# Seed 0 of every character first, so a partial batch is already comparable. A failed walk is logged and skipped.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
walk() {  # walk, then build the run's hike.html (run name = --name or the config stem, plus _s<seed>)
  echo "=== $(date '+%F %T') $*"
  local cfg=$1 name seed; shift; name=$(basename "$cfg" .yaml)
  local args=("$@"); for ((i = 0; i < ${#args[@]}; i++)); do
    [ "${args[i]}" = --name ] && name=${args[i+1]}; [ "${args[i]}" = --seed ] && seed=${args[i+1]}; done
  if $PY -m agent.walk "$cfg" "$@"; then $PY analysis/hike_viewer.py "runs/${name}_s${seed}" 2>&1 | grep '^\[hike\]'
  else echo "=== FAILED: $cfg $*"; fi
}
for c in bored globalist localist fastlearner; do walk configs/h2910_$c.yaml --seed 0; done
walk configs/global_perception.yaml --steps 1000 --name global_perception_1k --seed 1
for c in bored globalist localist fastlearner; do walk configs/h2910_$c.yaml --seed 1; done
echo "=== $(date '+%F %T') all done"
