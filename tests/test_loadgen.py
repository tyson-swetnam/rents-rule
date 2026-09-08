import importlib.util
import random
import statistics
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("load_generator", ROOT / "benchmarks" / "inference" / "load_generator.py")
lg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lg)


def test_sample_length_distributions():
    rng = random.Random(0)
    assert lg.sample_length("fixed", 128, rng) == 128
    ex = [lg.sample_length("exponential", 100, rng) for _ in range(20000)]
    assert statistics.mean(ex) == pytest.approx(100, rel=0.05)
    pa = [lg.sample_length("pareto", 100, rng, alpha=2.5) for _ in range(50000)]
    assert statistics.mean(pa) == pytest.approx(100, rel=0.08)
    assert min(pa) >= 1
    assert max(lg.sample_length("pareto", 100, rng, alpha=1.2, maximum=500) for _ in range(5000)) <= 500
    with pytest.raises(ValueError):
        lg.sample_length("pareto", 100, rng, alpha=1.0)
    with pytest.raises(ValueError):
        lg.sample_length("weird", 100, rng)


def test_poisson_schedule_rate():
    rng = random.Random(1)
    s = lg.poisson_schedule(rate=50.0, duration=200.0, rng=rng)
    assert len(s) == pytest.approx(10000, rel=0.05)
    assert all(0 < t <= 200 for t in s)
    assert s == sorted(s)


def test_prompt_words():
    rng = random.Random(2)
    assert len(lg.make_prompt(37, rng).split()) == 37
