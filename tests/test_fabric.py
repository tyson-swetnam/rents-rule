import pytest

from rentscale import fabric as fb

IBND = '''#
# Topology file: generated on Mon Sep  1 10:00:00 2026
#
vendid=0x2c9
devid=0xd2f2
switchguid=0xb8cef60300e5d2a0(b8cef60300e5d2a0)
Switch\t40 "S-b8cef60300e5d2a0"\t\t# "MF0;leaf-1:MQM8790/U1" enhanced port 0 lid 1 lmc 0
[1]\t"H-0c42a10300a1b2c4"[1](c42a10300a1b2c4) \t\t# "node01 mlx5_0" lid 5 4xHDR
[2]\t"H-0c42a10300a1b2c8"[1](c42a10300a1b2c8) \t\t# "node02 mlx5_0" lid 6 4xHDR
[3]\t"H-0c42a10300a1b2cc"[1](c42a10300a1b2cc) \t\t# "node03 mlx5_0" lid 7 4xHDR
[4]\t"H-0c42a10300a1b2d0"[1](c42a10300a1b2d0) \t\t# "node04 mlx5_0" lid 8 4xHDR
[21]\t"S-b8cef60300e5d2b0"[1]\t\t# "MF0;spine-1:MQM8790/U1" lid 2 4xHDR
[22]\t"S-b8cef60300e5d2b0"[2]\t\t# "MF0;spine-1:MQM8790/U1" lid 2 4xHDR

vendid=0x2c9
devid=0xd2f2
switchguid=0xb8cef60300e5d2b0(b8cef60300e5d2b0)
Switch\t40 "S-b8cef60300e5d2b0"\t\t# "MF0;spine-1:MQM8790/U1" enhanced port 0 lid 2 lmc 0
[1]\t"S-b8cef60300e5d2a0"[21]\t\t# "MF0;leaf-1:MQM8790/U1" lid 1 4xHDR
[2]\t"S-b8cef60300e5d2a0"[22]\t\t# "MF0;leaf-1:MQM8790/U1" lid 1 4xHDR

vendid=0x2c9
devid=0x101b
caguid=0x0c42a10300a1b2c4
Ca\t1 "H-0c42a10300a1b2c4"\t\t# "node01 mlx5_0"
[1](c42a10300a1b2c4) \t"S-b8cef60300e5d2a0"[1]\t\t# lid 1 lmc 0 "MF0;leaf-1:MQM8790/U1" lid 5 4xHDR

Ca\t1 "H-0c42a10300a1b2c8"\t\t# "node02 mlx5_0"
[1](c42a10300a1b2c8) \t"S-b8cef60300e5d2a0"[2]\t\t# lid 1 lmc 0 "MF0;leaf-1:MQM8790/U1" lid 6 4xHDR
'''


def test_parse_ibnetdiscover_dedupes_links_and_classifies():
    G = fb.parse_ibnetdiscover(IBND)
    assert G.number_of_edges() == 6  # 4 host links + 2 uplinks, each listed from both ends
    kinds = {n: d["kind"] for n, d in G.nodes(data=True)}
    assert kinds["S-b8cef60300e5d2a0"] == "switch" and kinds["H-0c42a10300a1b2c4"] == "ca"
    assert kinds["H-0c42a10300a1b2cc"] == "ca"  # only seen as a link target
    assert fb.classify_switches(G) == {"S-b8cef60300e5d2a0": "leaf", "S-b8cef60300e5d2b0": "spine"}
    s = fb.fabric_summary(G)
    assert s["hcas"] == 4 and s["leaf_switches"] == 1 and s["spine_switches"] == 1
    assert s["link_rates"] == {"4xHDR": 6}


def test_leaf_modules_oversubscription():
    G = fb.parse_ibnetdiscover(IBND)
    lm = fb.leaf_modules(G, gates_for_host=lambda desc: 5e11)
    assert len(lm) == 1
    r = lm.iloc[0]
    assert r.n_hosts == 4 and r.gates == 4 * 5e11
    assert r.links == 2 and r.lanes == 8 and r.gbps == 2 * 200
    assert r.downlinks == 4 and r.oversubscription == pytest.approx(2.0)
    assert "leaf-1" in r.leaf


def test_expand_hostlist():
    assert fb.expand_hostlist("node[01-03]") == ["node01", "node02", "node03"]
    assert fb.expand_hostlist("gpu[1-2,5],cpu7") == ["gpu1", "gpu2", "gpu5", "cpu7"]
    assert fb.expand_hostlist("a[1-2]b[1-2]") == ["a1b1", "a1b2", "a2b1", "a2b2"]
    assert fb.expand_hostlist("") == []


def test_slurm_topology():
    text = "SwitchName=root Level=1 LinkSpeed=1 Switches=leaf[1-2]\nSwitchName=leaf1 Level=0 LinkSpeed=1 Nodes=node[01-04]\nSwitchName=leaf2 Level=0 LinkSpeed=1 Nodes=node[05-06]\n"
    G = fb.parse_slurm_topology(text)
    tbl = fb.slurm_topology_table(G)
    by = {r.switch: r for _, r in tbl.iterrows()}
    assert by["leaf1"].n_hosts == 4 and by["leaf2"].n_hosts == 2 and by["root"].n_hosts == 6
    assert by["root"].level == 1
