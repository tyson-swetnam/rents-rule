import pytest

from rentscale import benchparse as bp

NCCL = """# nThread 1 nGpus 1 minBytes 8 maxBytes 8589934592 step: 2(factor) warmup iters: 5 iters: 20 agg iters: 1 validation: 0 graph: 0
#
# Using devices
#  Rank  0 Group  0 Pid  100 on node01 device  0 [0x07] NVIDIA A100-SXM4-40GB
#
#                                                              out-of-place                       in-place
#       size         count      type   redop    root     time   algbw   busbw #wrong     time   algbw   busbw #wrong
#        (B)    (elements)                               (us)  (GB/s)  (GB/s)            (us)  (GB/s)  (GB/s)
           8             2     float     sum      -1    34.50    0.00    0.00      0    33.98    0.00    0.00      0
     1048576        262144     float     sum      -1    45.12   23.24   40.67      0    44.90   23.35   40.87      0
  8589934592    2147483648     float     sum      -1 41234.00  208.32  364.56      0 41200.00  208.49  364.86      0
# Out of bounds values : 0 OK
# Avg bus bandwidth    : 135.0767
#
"""


def test_parse_nccl():
    df = bp.parse_nccl_tests(NCCL)
    assert len(df) == 3
    assert list(df.columns[:5]) == ["size", "count", "type", "redop", "root"]
    assert "busbw_oop" in df.columns and "busbw_ip" in df.columns
    assert df.iloc[-1].busbw_oop == 364.56
    assert bp.nccl_peak_busbw(df) == 364.56
    assert bp.nccl_avg_bus_bandwidth(NCCL) == pytest.approx(135.0767)
    assert bp.delivered_terminal_capacity(8, 364.56) == pytest.approx(8 * 364.56)


OSU = """# OSU MPI All-to-All Personalized Exchange Latency Test v7.3
# Datatype: MPI_CHAR.
# Size       Avg Latency(us)   Min Latency(us)   Max Latency(us)  Iterations
1                       4.34              4.10              4.60        1000
1048576              1234.56           1200.00           1300.00         100
"""


def test_parse_osu():
    df = bp.parse_osu(OSU)
    assert len(df) == 2
    assert df.iloc[1]["size"] == 1048576 and df.iloc[1]["value"] == 1234.56
    assert df.iloc[1].value2 == 1200.0 and df.iloc[1].value4 == 100
    assert df.attrs["metric"].startswith("Size")
    assert "All-to-All" in df.attrs["title"]


PERFTEST = """---------------------------------------------------------------------------------------
                    RDMA_Write BW Test
 Dual-port       : OFF\t\tDevice         : mlx5_0
---------------------------------------------------------------------------------------
 #bytes     #iterations    BW peak[Gb/sec]    BW average[Gb/sec]   MsgRate[Mpps]
 1048576    5000             196.84             196.71             0.023455
---------------------------------------------------------------------------------------
"""


def test_parse_perftest():
    df = bp.parse_perftest(PERFTEST)
    assert len(df) == 1
    assert df.iloc[0].bytes == 1048576 and df.iloc[0].bw_avg == 196.71
    assert "Gb/sec" in df.attrs["header"]
