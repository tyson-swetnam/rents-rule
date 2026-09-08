"""The energy-time minimization model of Moses, Bezerra, Edwards, Brown & Forrest (2016),
*Energy and time determine scaling in biological and computer designs*, Phil. Trans. R.
Soc. B 371:20150446 (PMC4958940), and its extension to the data-center regime.

A hierarchical network has branching factor ``lam``, ``H`` levels and ``N = lam**H``
terminal nodes; level 0 is the smallest (capillaries, transistors, GPUs). Lengths,
thicknesses and link counts scale with level ``i`` as

    l_i = l_0 * lam**(i / D_l)     (2.1)  D_l: spatial dimension of the layout (2 chips, 3 organisms)
    r_i = r_0 * lam**(i / D_r)     (2.2)  D_r: thickness / bandwidth dimension (2 = area preserving)
    w_i = w_0 * lam**(i / D_w)     (2.3)  D_w: communication dimension; Rent's exponent p = 1 / D_w

``E_sys = E_net + E_node`` and ``T_sys`` are minimized jointly (the energy-delay product).
Paper regime ("chips"): nodes shrink as N grows on a fixed area, ``l_0, r_0 ~ N**(-1/D_l)``.
Data-center regime (this project): nodes have fixed size and N grows by adding area or
volume, so ``l_0`` and ``r_0`` are constants. Exponents below are exponents of N.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

OPTIMAL_DR_MAMMAL = 24.0 / 11.0  # D_r that keeps T_node invariant while blood slows (paper §3b)
_EPS = 1e-12


# ----------------------------------------------------------------------------- dimensions
def rent_exponent(D_w: float) -> float:
    """Rent's exponent ``p = 1 / D_w`` (paper, endnote 1)."""
    return 1.0 / D_w


def communication_dimension(p: float) -> float:
    """``D_w = 1 / p``."""
    if p <= 0:
        raise ValueError("p must be positive")
    return 1.0 / p


def series_exponent(D_l: float, D_w: float) -> float:
    """Exponent ``a`` in the wire-length sum ``sum_i lam**(i a)``: ``a = 1/D_l + 1/D_w - 1``
    (paper eq. 3.10). Negative ``a`` means the sum converges (short wires dominate)."""
    return 1.0 / D_l + 1.0 / D_w - 1.0


def locality_threshold(D_l: float) -> float:
    """Minimum communication dimension for a convergent network energy,
    ``D_w >= D_l / (D_l - 1)`` — equivalently ``p <= 1 - 1/D_l`` (Ozaktas' embedding bound)."""
    if D_l <= 1:
        raise ValueError("D_l must exceed 1")
    return D_l / (D_l - 1.0)


def geometric_sum(lam: float, a: float, H: float) -> float:
    """``sum_{i=0}^{H} lam**(i a)`` for integer ``H`` (closed form; ``H + 1`` when ``a = 0``)."""
    n = int(round(H)) + 1
    q = lam**a
    if abs(q - 1.0) < _EPS:
        return float(n)
    return float((q**n - 1.0) / (q - 1.0))


def levels(N: float, lam: float) -> float:
    return math.log(N) / math.log(lam)


# ----------------------------------------------------------------------------- totals
def total_wire_length(
    N: float, lam: float, D_l: float, D_w: float, l0: float = 1.0, w0: float = 1.0, shrink: bool = False
) -> float:
    """``sum_i l_i w_i n_i`` (paper eq. 3.9): total wire length, proportional to the network
    capacitance and hence ``E_net``. ``shrink=True`` applies the chip rule ``l_0 ~ N**(-1/D_l)``."""
    H = levels(N, lam)
    if shrink:
        l0 = l0 * N ** (-1.0 / D_l)
    return l0 * w0 * N * geometric_sum(lam, series_exponent(D_l, D_w), H)


def total_links(N: float, lam: float, D_w: float, w0: float = 1.0) -> float:
    """``sum_i w_i n_i``: total links / ports / transceivers (no length factor).
    Linear in N for ``D_w > 1`` (``p < 1``), ``N log N`` at ``p = 1``."""
    H = levels(N, lam)
    return w0 * N * geometric_sum(lam, 1.0 / D_w - 1.0, H)


# ----------------------------------------------------------------------------- exponents
@dataclass(frozen=True)
class Exponents:
    """Exponents of N for the terms of the energy-time product. ``energy_time`` is the
    exponent of ``E_sys * T_sys``; ``power`` of ``E_sys / T_sys``; ``throughput`` of
    ``N / T_sys``; ``per_node`` of the energy-time product per node."""

    regime: str
    E_net: float
    E_node: float
    T_net: float
    T_node: float
    energy_time: float
    power: float
    throughput: float
    per_node: float
    log_factor: bool
    notes: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _combine(regime, E_net, E_node, T_net, T_node, log_factor, notes=""):
    E_sys = max(E_net, E_node)
    T_sys = max(T_net, T_node)
    return Exponents(
        regime=regime,
        E_net=E_net,
        E_node=E_node,
        T_net=T_net,
        T_node=T_node,
        energy_time=E_sys + T_sys,
        power=E_sys - T_sys,
        throughput=1.0 - T_sys,
        per_node=E_sys + T_sys - 1.0,
        log_factor=log_factor,
        notes=notes,
    )


def chip_exponents(D_l: float = 2.0, D_r: float = 2.0, D_w: float = 2.0) -> Exponents:
    """Paper regime (Table 1, 'computers'): nodes shrink on a fixed area.

    * ``E_net ~ N**(1 - 1/D_l)`` when ``D_w >= D_l/(D_l - 1)`` (log N factor at equality),
      else ``N**(1/D_w)``;
    * ``E_node ~ N l_0 ~ N**(1 - 1/D_l)``;
    * ``T_net ~ N**0`` (constant wire delay; requires ``D_r = 2`` for perfect pipelining);
    * ``T_node ~ l_0 ~ N**(-1/D_l)``.

    With ``D_l = D_r = D_w = 2`` (Dennard scaling, Rent p = 1/2): power ``~ N**(1/2)``
    (measured 0.495) and throughput ``~ N`` (measured 1.11)."""
    a = series_exponent(D_l, D_w)
    if a < -_EPS:
        E_net, log_factor = 1.0 - 1.0 / D_l, False
    elif abs(a) <= _EPS:
        E_net, log_factor = 1.0 - 1.0 / D_l, True
    else:
        E_net, log_factor = 1.0 / D_w, False
    E_node = 1.0 - 1.0 / D_l
    T_node = -1.0 / D_l
    if abs(D_r - 2.0) <= _EPS:
        T_net, notes = 0.0, ""
    else:
        T_net, notes = 0.0, "T_net = N^0 assumes perfect pipelining, which the paper's Appendix B shows requires D_r = 2"
    return _combine("chip", E_net, E_node, T_net, T_node, log_factor, notes)


def datacenter_exponents(
    D_l: float = 2.0, p: float = 0.5, oversubscription: float = 1.0, lam: float | None = None
) -> Exponents:
    """Data-center regime: nodes of fixed size, N grows by adding floor area (``D_l = 2``)
    or volume (``D_l = 3``); ``p`` is the hardware Rent exponent of the fabric.

    * ``E_net`` (wire length, i.e. cable-metres and the energy to drive them):
      ``N`` when ``p < 1 - 1/D_l``, ``N log N`` at equality, ``N**(p + 1/D_l)`` above;
    * ``E_node ~ N`` (fixed energy per node, as for cells);
    * ``T_net ~ N**0`` for a non-blocking fabric; with per-level oversubscription ``r``
      the top-level delivery time of a bit grows as ``r**H = N**(ln r / ln lam)``;
    * ``T_node ~ N**0``.

    The energy-time product per node is therefore flat at best (constant returns), and the
    chip regime's improving ``N**(-1/D_l)`` per node is gone: this is the 'end of Dennard
    scaling' stated in the model's own variables."""
    if not 0 < p <= 1:
        raise ValueError("p must be in (0, 1]")
    if oversubscription < 1:
        raise ValueError("oversubscription is downlink/uplink capacity, >= 1")
    D_w = communication_dimension(p)
    a = series_exponent(D_l, D_w)
    if a < -_EPS:
        E_net, log_factor = 1.0, False
    elif abs(a) <= _EPS:
        E_net, log_factor = 1.0, True
    else:
        E_net, log_factor = 1.0 + a, False  # = p + 1/D_l
    E_node = 1.0
    T_node = 0.0
    notes = ""
    if oversubscription > 1.0:
        if lam is None:
            raise ValueError("lam (branching factor) is needed to convert oversubscription to an exponent")
        T_net = math.log(oversubscription) / math.log(lam)
        notes = "T_net exponent applies to traffic that must cross the top level; local traffic sees N^0"
    else:
        T_net = 0.0
    return _combine("datacenter", E_net, E_node, T_net, T_node, log_factor, notes)


def mammal_exponents(D_l: float = 3.0, D_r: float = 2.0) -> Exponents:
    """Paper regime (Table 1, 'mammals') with ``l_0`` and ``u_0`` held constant:
    ``E_net ~ N**(2/D_r - 1)`` when ``D_r <= 4 D_l / (1 + D_l)`` (Case 1), else
    ``N**(1/D_l - 2/D_r)``; ``E_node ~ N``; ``T_net = T_node ~ N**(1 - 2/D_r)``.
    Area-preserving branching (``D_r = 2``) gives constant network energy per unit of
    blood and constant delivery time; the paper's optimum with blood slowing is
    ``D_r = 24/11``."""
    if D_r <= 4.0 * D_l / (1.0 + D_l) + _EPS:
        E_net = 2.0 / D_r - 1.0
    else:
        E_net = 1.0 / D_l - 2.0 / D_r
    E_node = 1.0
    T = 1.0 - 2.0 / D_r
    return _combine("mammal", E_net, E_node, T, T, False, "l_0 and u_0 held constant; see paper §3a-b for their N-dependence")


def summary_table() -> pd.DataFrame:
    """The regimes side by side (exponents of N)."""
    rows = [
        ("chips, Dennard (D_l=D_r=D_w=2)", chip_exponents(2, 2, 2)),
        ("chips, 3-D stacking (D_l=3, D_w=1.5)", chip_exponents(3, 2, 1.5)),
        ("data center 2-D floor, p=0.5", datacenter_exponents(2, 0.5)),
        ("data center 2-D floor, p=0.8", datacenter_exponents(2, 0.8)),
        ("data center 2-D floor, p=1 (full bisection)", datacenter_exponents(2, 1.0)),
        ("data center 3-D, p=0.5", datacenter_exponents(3, 0.5)),
        ("mammals, D_r=2 (WBE)", mammal_exponents(3, 2.0)),
        ("mammals, D_r=24/11 (paper optimum)", mammal_exponents(3, OPTIMAL_DR_MAMMAL)),
    ]
    out = []
    for name, e in rows:
        d = e.as_dict()
        d["case"] = name
        out.append(d)
    cols = ["case", "regime", "E_net", "E_node", "T_net", "T_node", "energy_time", "power", "throughput", "per_node", "log_factor"]
    return pd.DataFrame(out)[cols]
