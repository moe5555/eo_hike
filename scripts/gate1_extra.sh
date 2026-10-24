#!/usr/bin/env bash
# Added after the first Gate 1 runs: surprise_only, and the TV test (start next to the TV).
set -e
for c in surprise_only tvtest_baseline tvtest_novelty_only tvtest_surprise_only; do
  for s in 0 1; do
    .venv/Scripts/python -m agent.walk configs/$c.yaml --seed $s
  done
done
