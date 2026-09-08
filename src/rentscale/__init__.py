"""rentscale: Rent's rule, self-similar traffic, and metabolic-scaling analysis for data
center hierarchies (die -> package -> node -> rack -> pod -> facility -> WAN).

Modules
-------
rent        power-law / Rent fits, locality steps between levels
topology    synthetic fat-trees, tapered trees, meshes; (G, T) extraction from any graph
hurst       fGn synthesis and Hurst / spectral estimators
counters    cumulative counter -> rate conversion; nvidia-smi / dcgmi / ethtool parsers
benchparse  nccl-tests, OSU, perftest output parsers
scaling     returns to scale, PUE model, dimension bounds, size trade-off
inventory   node inventory parsers and the hierarchy-YAML Rent census
fabric      ibnetdiscover / Slurm topology parsers -> leaf-level Rent points
energytime  Moses et al. (2016) energy-time minimization model and its data-center regime
"""

__version__ = "0.1.0"

from .rent import (  # noqa: F401
    PowerLawFit,
    RentFit,
    fit_power_law,
    fit_rent,
    locality_step_from_p,
    locality_steps,
    p_from_locality_step,
)
