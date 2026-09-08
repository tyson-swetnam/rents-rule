import json
from pathlib import Path

import pytest

from rentscale import inventory as inv

NVSMI = """index, name, uuid, pci.bus_id, pcie.link.gen.max, pcie.link.gen.current, pcie.link.width.max, pcie.link.width.current, memory.total [MiB], power.limit [W], driver_version
0, NVIDIA A100-SXM4-80GB, GPU-1, 00000000:07:00.0, 4, 4, 16, 16, 81920 MiB, 400.00 W, 535.104.12
1, NVIDIA A100-SXM4-80GB, GPU-2, 00000000:0F:00.0, 4, 4, 16, 16, 81920 MiB, 400.00 W, 535.104.12
"""

TOPO = "\tGPU0\tGPU1\tmlx5_0\tCPU Affinity\tNUMA Affinity\nGPU0\t X \tNV12\tPXB\t0-63\t0\nGPU1\tNV12\t X \tSYS\t64-127\t1\nmlx5_0\tPXB\tSYS\t X \t\t\n\nLegend:\n  X = Self\n"

LSCPU = json.dumps(
    {
        "lscpu": [
            {"field": "Architecture:", "data": "x86_64"},
            {"field": "Model name:", "data": "AMD EPYC 7763 64-Core Processor"},
            {"field": "Socket(s):", "data": "2"},
            {"field": "Core(s) per socket:", "data": "64"},
            {"field": "Thread(s) per core:", "data": "2"},
        ]
    }
)

IBSTAT = """CA 'mlx5_0'
\tCA type: MT4123
\tNumber of ports: 1
\tFirmware version: 20.28.1002
\tPort 1:
\t\tState: Active
\t\tPhysical state: LinkUp
\t\tRate: 200
\t\tBase lid: 12
\t\tLink layer: InfiniBand
CA 'mlx5_1'
\tCA type: MT4123
\tNumber of ports: 1
\tPort 1:
\t\tState: Down
\t\tPhysical state: Disabled
\t\tRate: 10
\t\tLink layer: InfiniBand
CA 'mlx5_2'
\tCA type: MT4125
\tNumber of ports: 1
\tPort 1:
\t\tState: Active
\t\tPhysical state: LinkUp
\t\tRate: 100
\t\tLink layer: Ethernet
"""

IB_SYSFS = "device=mlx5_0 port=1\nstate=4: ACTIVE\nphys_state=5: LinkUp\nrate=200 Gb/sec (4X HDR)\nlink_layer=InfiniBand\n"
ETHTOOL_UP = "Settings for ens1f0:\n\tSpeed: 25000Mb/s\n\tDuplex: Full\n\tPort: FIBRE\n\tLink detected: yes\n"
ETHTOOL_DOWN = "Settings for eno1:\n\tSpeed: Unknown!\n\tLink detected: no\n"


def test_match_part_by_alias_and_key():
    tt = inv.load_transistor_table()
    assert inv.match_part("NVIDIA A100-SXM4-80GB", tt)["key"] == "nvidia-a100"
    assert inv.match_part("AMD EPYC 7763 64-Core Processor", tt)["key"] == "amd-epyc-7763"
    assert inv.match_part("nvidia-h100", tt)["key"] == "nvidia-h100"
    assert inv.match_part("Intel(R) Xeon(R) Platinum 8380 CPU @ 2.30GHz", tt)["key"] == "intel-xeon-8380"
    assert inv.match_part("Some Unknown Chip", tt) is None


def test_parsers():
    gpus = inv.parse_nvidia_smi_query_csv(NVSMI)
    assert len(gpus) == 2 and gpus[0]["name"] == "NVIDIA A100-SXM4-80GB"
    assert gpus[0]["pcie.link.gen.max"] == 4 and gpus[0]["memory.total"] == 81920
    m = inv.parse_nvidia_smi_topo(TOPO)
    assert m["GPU0"]["GPU1"] == "NV12" and m["GPU0"]["mlx5_0"] == "PXB"
    assert inv.nvlink_counts_from_topo(m) == {"GPU0": 12, "GPU1": 12}
    ports = inv.parse_ibstat(IBSTAT)
    assert [p["state"] for p in ports] == ["Active", "Down", "Active"]
    assert ports[0]["rate_gbps"] == 200 and ports[2]["link_layer"] == "Ethernet"
    assert inv.parse_ib_sysfs(IB_SYSFS)[("mlx5_0", 1)]["width"] == 4
    assert inv.parse_ethtool_link(ETHTOOL_UP) == {"speed_mbps": 25000, "link": True, "port_type": "FIBRE"}
    assert inv.parse_ethtool_link(ETHTOOL_DOWN)["link"] is False


def test_node_summary(tmp_path: Path):
    d = tmp_path / "node01"
    d.mkdir()
    (d / "meta.txt").write_text("hostname=node01\n")
    (d / "nvidia-smi_query.csv").write_text(NVSMI)
    (d / "nvidia-smi_topo.txt").write_text(TOPO)
    (d / "lscpu.json").write_text(LSCPU)
    (d / "ibstat.txt").write_text(IBSTAT)
    (d / "ib_sysfs.txt").write_text(IB_SYSFS)
    (d / "ethtool_ens1f0.txt").write_text(ETHTOOL_UP)
    (d / "ethtool_eno1.txt").write_text(ETHTOOL_DOWN)
    s = inv.node_summary(d)
    assert s["host"] == "node01"
    assert s["gates"] == pytest.approx(2 * 54.2e9 + 2 * 41.5e9)
    assert s["cpu"]["sockets"] == 2 and s["cpu"]["part_key"] == "amd-epyc-7763"
    assert len(s["ib_ports"]) == 1  # only the Active InfiniBand port; RoCE port is skipped here
    assert s["eth_ports"] == [{"iface": "ens1f0", "speed_mbps": 25000, "lanes": 1, "port_type": "FIBRE"}]
    assert s["terminals"] == {"lanes": 5, "ports": 2, "gbps": 225.0}
    g0 = s["gpus"][0]
    assert g0["nvlinks"] == 12
    assert g0["terminals"]["lanes"] == 12 * 4 + 16
    assert g0["terminals"]["gbps"] == pytest.approx(12 * 200 + 16 * 15.754)
    assert s["unknown_parts"] == [] and s["missing"] == []


def test_census_example_group_fits():
    h = inv.load_hierarchy(inv.REF_DIR / "hierarchy_template.yaml")
    df = inv.census(h, group="example")
    assert set(df.level) == {"die", "node", "rack", "leaf-group", "pod", "facility"}
    die = df[df.module == "example-a100-die"].iloc[0]
    node = df[df.module == "example-gpu-node"].iloc[0]
    assert die.gates == pytest.approx(54.2e9)
    assert node.gates == pytest.approx(8 * 54.2e9 + 2 * 39.5e9)
    assert die.lanes == 12 * 4 + 16 and node.lanes == 10 * 4 + 2 * 4
    assert (df.unknown_parts == "").all() and (df.unknown_links == "").all()
    rep = inv.census_report(df, bootstrap=0)
    steps = {(s["from"], s["to"]): s for s in rep["steps"]["gbps"]}
    # die -> node: the pin-limited step (fewer Gb/s leave the node than leave one GPU)
    assert steps[("example-a100-die", "example-gpu-node")]["local_exponent"] < 0
    # rack -> leaf-group -> pod: full bisection, lambda = 1 for the compute fabric (+ eth)
    assert steps[("example-rack", "example-leaf-group")]["local_exponent"] == pytest.approx(1.0, abs=0.05)
    assert steps[("example-leaf-group", "example-pod")]["lambda"] == pytest.approx(1.0, abs=0.05)
    # pod -> facility: the WAN step
    assert steps[("example-pod", "example-facility")]["lambda"] < 0.01
    assert "gbps" in rep["fits"] and rep["fits"]["gbps"].n == 6


def test_census_reports_unknowns_and_cycles():
    h = {
        "levels": ["node", "rack"],
        "modules": [
            {"name": "n", "level": "node", "parts": [{"part": "mystery-asic", "qty": 2}], "external_links": [{"link": "no_such_link", "qty": 1}]},
            {"name": "r", "level": "rack", "children": [{"module": "n", "qty": 4}]},
        ],
    }
    df = inv.census(h)
    assert df[df.module == "n"].iloc[0].unknown_parts == "mystery-asic"
    assert df[df.module == "n"].iloc[0].unknown_links == "no_such_link"
    assert df[df.module == "r"].iloc[0].gates == 0
    bad = {"levels": ["a"], "modules": [{"name": "x", "level": "a", "children": [{"module": "y"}]}, {"name": "y", "level": "a", "children": [{"module": "x"}]}]}
    with pytest.raises(ValueError):
        inv.census(bad)
