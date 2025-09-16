# metrics.py
from typing import List, Dict, Tuple, Optional
from .config import BODY_WEIGHT_N, FORCE_THRESHOLD_RATIO, SENSOR_POS_M, HEEL_LABELS, TOE_LABELS, MID_LABELS, BALL_LABELS

def _total_force(f_by_label: Dict[str, float]) -> float:
    return sum(f_by_label.values())

def _cop_xy(f_by_label: Dict[str, float]) -> Tuple[float, float]:
    # Center of Pressure (x,y) in meters (weighted by force)
    sF = _total_force(f_by_label)
    if sF <= 0.0: return (0.0, 0.0)
    sx = sum(f_by_label.get(lbl,0.0) * SENSOR_POS_M[lbl][0] for lbl in SENSOR_POS_M)
    sy = sum(f_by_label.get(lbl,0.0) * SENSOR_POS_M[lbl][1] for lbl in SENSOR_POS_M)
    return (sx/sF, sy/sF)

def _subset_force(f_by_label: Dict[str, float], subset: set) -> float:
    return sum(v for k, v in f_by_label.items() if k in subset)

def detect_events(times_s: List[float], forces_series: List[Dict[str, float]],
                  body_weight_N: Optional[float]=BODY_WEIGHT_N,
                  thr_ratio: float=FORCE_THRESHOLD_RATIO):
    """
    Returns dict with HS indices, TO indices, stance & swing windows, COP path.
    """
    if not times_s or not forces_series: 
        return {"HS":[], "TO":[], "stance":[], "swing":[], "COP": []}

    # total force curve
    Ft = [ _total_force(f) for f in forces_series ]

    # threshold
    if body_weight_N and body_weight_N > 0:
        thr = thr_ratio * body_weight_N
    else:
        # auto: 5% of median of top decile
        top = sorted(Ft)[max(0,int(0.9*len(Ft))):]
        ref = top[len(top)//2] if top else (max(Ft) if Ft else 0.0)
        thr = thr_ratio * ref

    HS, TO = [], []
    above = False
    for i in range(1, len(Ft)):
        if not above and Ft[i-1] < thr <= Ft[i]:
            HS.append(i)
            above = True
        elif above and Ft[i-1] >= thr > Ft[i]:
            TO.append(i)
            above = False

    # pair into stance/swing
    stance, swing = [], []
    ti = 0
    for hs in HS:
        # find the first TO after this HS
        while ti < len(TO) and TO[ti] < hs:
            ti += 1
        if ti < len(TO):
            stance.append((hs, TO[ti]))
            # swing: TO -> next HS (if any)
            nxt_hs_idx = None
            for h2 in HS:
                if h2 > TO[ti]:
                    nxt_hs_idx = h2; break
            if nxt_hs_idx is not None:
                swing.append((TO[ti], nxt_hs_idx))
            ti += 1

    # COP path (for plotting/analysis)
    COP = []
    for t, f in zip(times_s, forces_series):
        x,y = _cop_xy(f)
        COP.append({"t": t, "x": x, "y": y})

    # heel-vs-forefoot ordering (optional: first peak comparison)
    # You can add diagnostics here using _subset_force() over windows around HS.

    return {"HS":HS, "TO":TO, "stance":stance, "swing":swing, "COP":COP, "threshold":thr}

def temporal_metrics(times_s: List[float], HS: List[int], TO: List[int], stance: List[Tuple[int,int]]):
    # Contact Time (CT)
    CT = [ times_s[to]-times_s[hs] for (hs,to) in stance ]

    # Flight Time (FT): TO_prev -> HS_next (same foot)
    FT = []
    for i in range(1, len(HS)):
        # find TO just before this HS
        to_prev = None
        for to in reversed(TO):
            if to < HS[i]:
                to_prev = to; break
        if to_prev is not None:
            FT.append(times_s[HS[i]] - times_s[to_prev])

    # Stride duration (HS_i -> HS_{i+1})
    stride = [ times_s[HS[i+1]] - times_s[HS[i]] for i in range(len(HS)-1) ]

    # Frequency
    stride_freq = (1.0 / (sum(stride)/len(stride))) if stride else 0.0

    return {"CT":CT, "FT":FT, "stride":stride, "stride_freq":stride_freq}
