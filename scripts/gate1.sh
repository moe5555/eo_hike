#!/usr/bin/env bash
# Gate 1: all six temperaments x 2 seeds, same start tile.
set -e
for c in random baseline novelty_only myopic wide restless; do
  for s in 0 1; do
    .venv/Scripts/python -m agent.walk configs/$c.yaml --seed $s
  done
done
