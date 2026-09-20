import numpy as np
import pytest
import torch
from PIL import Image

from hiker.heatmap import centre_patches, patch_novelty, render_overlay
from hiker.scoring import novelty_scores


def unit_rows(n, d, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_patch_novelty_matches_chip_novelty_formula():
    q = unit_rows(7, 16, 1)
    bank = unit_rows(40, 16, 2)
    got = patch_novelty(torch.from_numpy(q), torch.from_numpy(bank), 5).numpy()
    want = novelty_scores(q, bank, 5)
    assert np.allclose(got, want, atol=1e-5)


def test_patch_novelty_small_bank_uses_all_of_it():
    q = unit_rows(3, 8, 1)
    bank = unit_rows(2, 8, 2)
    got = patch_novelty(torch.from_numpy(q), torch.from_numpy(bank), 15).numpy()
    want = (1 - q @ bank.T).mean(axis=1)
    assert np.allclose(got, want, atol=1e-5)


def test_patch_novelty_rejects_bad_inputs():
    q = torch.from_numpy(unit_rows(3, 8, 1))
    with pytest.raises(ValueError):
        patch_novelty(q, torch.zeros((0, 8)), 5)
    with pytest.raises(ValueError):
        patch_novelty(q, q, 0)


def test_centre_patches_normalises_and_centres():
    t = np.random.default_rng(0).normal(size=(2, 5, 8)).astype(np.float32) + 3.0
    plain = centre_patches(t, None)
    assert np.allclose(np.linalg.norm(plain, axis=-1), 1.0, atol=1e-5)
    mean = plain.reshape(-1, 8).mean(axis=0)
    centred = centre_patches(t, mean)
    assert np.allclose(np.linalg.norm(centred, axis=-1), 1.0, atol=1e-5)
    # the common component is gone: the centred vectors no longer all point the same way
    assert np.abs(centred.reshape(-1, 8).mean(axis=0)).max() < np.abs(mean).max()


def test_render_overlay_tints_only_hot_patches(tmp_path):
    src = tmp_path / "chip.png"
    Image.new("RGB", (64, 64), (100, 100, 100)).save(src)
    scores = np.zeros((4, 4), dtype=np.float32)
    scores[0, 0] = 1.0
    out = tmp_path / "heat.png"
    render_overlay(src, scores, vmin=0.0, vmax=1.0, alpha=0.6, cmap="inferno", out=out)
    im = np.asarray(Image.open(out).convert("RGB")).astype(int)
    assert im.shape == (64, 64, 3)
    assert not np.array_equal(im[2, 2], [100, 100, 100])  # hot corner is tinted
    assert np.array_equal(im[60, 60], [100, 100, 100])  # cold corner untouched
