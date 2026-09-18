import json

import numpy as np
import pytest

from hiker.config import config_hash, load_config, parse_override
from hiker.io import JsonlWriter, geo_distance_or_none, haversine_km, time_delta_days_or_none


def test_haversine_known_distance():
    # Paris -> Sydney is roughly 16,960 km
    assert haversine_km(48.8566, 2.3522, -33.8688, 151.2093) == pytest.approx(16960, rel=0.01)


def test_geo_none_when_missing():
    assert geo_distance_or_none({"lat": 1.0, "lon": 2.0}, {"lat": None, "lon": 2.0}) is None
    assert geo_distance_or_none({"lat": float("nan"), "lon": 2.0}, {"lat": 1.0, "lon": 2.0}) is None


def test_time_delta_signed_days():
    assert time_delta_days_or_none({"date": "2020-01-01"}, {"date": "2019-12-30"}) == -2
    assert time_delta_days_or_none({"date": None}, {"date": "2019-12-30"}) is None


def test_override_parsing_types():
    assert parse_override("agents.temperature=0.3") == {"agents": {"temperature": 0.3}}
    assert parse_override("dataset.max_shards=null") == {"dataset": {"max_shards": None}}
    assert parse_override("agents.start_chips=[a, b]") == {"agents": {"start_chips": ["a", "b"]}}


def test_config_hash_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("HIKER_DATA_ROOT", str(tmp_path))
    a = load_config(None, ["agents.seed=1"])
    b = load_config(None, ["agents.seed=1"])
    c = load_config(None, ["agents.seed=2"])
    assert config_hash(a) == config_hash(b) != config_hash(c)


def test_jsonl_writer_rounds_and_orders(tmp_path):
    p = tmp_path / "log.jsonl"
    with JsonlWriter(p, fields=["b", "a"]) as w:
        w.write({"a": np.float32(0.123456789), "b": np.int64(3), "zzz": "ignored"})
    line = p.read_text(encoding="utf-8").strip()
    assert line == '{"b": 3, "a": 0.123457}'
    assert json.loads(line)["a"] == 0.123457
