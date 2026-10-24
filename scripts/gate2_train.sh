#!/usr/bin/env bash
# Gate 2: three DDPMs per agent (same seed/arch/steps), then 64 samples each with the same noise seed.
# usage: bash scripts/gate2_train.sh baseline_s0 [more run ids...]
set -e
for run in "$@"; do
  for s in path_weighted path_uniform random_uniform; do
    if [ ! -f runs/ddpm/$run/$s/ema/diffusion_pytorch_model.safetensors ] || [ ! -f runs/ddpm/$run/$s/samples.npy ]; then
      .venv/Scripts/python -m gen.train_ddpm data/sets/$run $s --steps 15000
      .venv/Scripts/python -m gen.sample runs/ddpm/$run/$s
    fi
  done
done
