import numpy as np
import pandas as pd
import pytest

from rentscale import counters as ct


def test_rates_with_wrap_and_groups():
    df = pd.DataFrame(
        {
            "t": [0.0, 0.1, 0.2, 0.3, 0.0, 0.1],
            "dev": ["a", "a", "a", "a", "b", "b"],
            "x": [100, 200, 2**32 - 50, 50, 10, 30],
        }
    )
    out = ct.rates_from_cumulative(df, "t", ["x"], group_cols=["dev"], wrap_bits=32, multiplier=4)
    a = out[out.dev == "a"]["x_per_s"].to_numpy()
    assert a[0] == pytest.approx(100 * 4 / 0.1)
    assert a[2] == pytest.approx(100 * 4 / 0.1)  # wrapped: (50 - (2^32-50)) + 2^32 = 100
    b = out[out.dev == "b"]["x_per_s"].to_numpy()
    assert b[0] == pytest.approx(20 * 4 / 0.1)
    assert (out["dt_s"] > 0).all()


def test_rates_negative_delta_without_wrap_is_nan():
    df = pd.DataFrame({"t": [0, 1, 2], "x": [10, 5, 20]})
    out = ct.rates_from_cumulative(df, "t", ["x"])
    assert np.isnan(out["x_per_s"].iloc[0])
    assert out["x_per_s"].iloc[1] == 15


NVLINK_TEXT = """GPU 0: NVIDIA A100-SXM4-40GB (UUID: GPU-aaaa)
\t Link 0: Data Tx: 12345 KiB
\t Link 0: Data Rx: 2048 KiB
\t Link 1: Data Tx: 0 KiB
\t Link 1: Data Rx: 1 MiB
GPU 1: NVIDIA A100-SXM4-40GB (UUID: GPU-bbbb)
\t Link 0: Data Tx: 7 KiB
\t Link 0: Data Rx: 9 KiB
"""


def test_parse_nvidia_smi_nvlink():
    df = ct.parse_nvidia_smi_nvlink_throughput(NVLINK_TEXT)
    assert len(df) == 3
    r = df[(df.gpu == 0) & (df.link == 0)].iloc[0]
    assert r.tx_bytes == 12345 * 1024 and r.rx_bytes == 2048 * 1024
    assert df[(df.gpu == 0) & (df.link == 1)].iloc[0].rx_bytes == 1024**2
    assert df[df.gpu == 1].iloc[0].tx_bytes == 7 * 1024


DCGMI_TEXT = """#Entity   NVLTX   NVLRX   PCITX  PCIRX   POWER
ID
GPU 0     1000    2000    300    400     251.2
GPU 1     N/A     10      0      0       80.0
"""


def test_parse_dcgmi_dmon():
    df = ct.parse_dcgmi_dmon(DCGMI_TEXT)
    assert list(df.columns) == ["entity", "id", "NVLTX", "NVLRX", "PCITX", "PCIRX", "POWER"]
    assert df.iloc[0].NVLTX == 1000 and df.iloc[0].POWER == 251.2
    assert np.isnan(df.iloc[1].NVLTX) and df.iloc[1].NVLRX == 10


def test_parse_ethtool_stats():
    text = "NIC statistics:\n     rx_packets: 12\n     tx_bytes: 34567\n     rx_queue_0_bytes: 5\n"
    d = ct.parse_ethtool_stats(text)
    assert d == {"rx_packets": 12, "tx_bytes": 34567, "rx_queue_0_bytes": 5}


def test_locality_fractions():
    df = ct.locality_fractions({"gpu": 8 * 4.6e6, "node": 16e3, "rack": 16e3}, ["gpu", "node", "rack"])
    assert df.iloc[0]["fraction_of_total"] > 0.99
    assert df.iloc[1]["lambda"] == pytest.approx(16e3 / (8 * 4.6e6))
    assert df.iloc[2]["lambda"] == pytest.approx(1.0)
    assert ct.bytes_per_unit_work(1000, 0) != ct.bytes_per_unit_work(1000, 0)  # NaN
