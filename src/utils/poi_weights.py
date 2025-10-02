
from typing import Dict

CRITICAL_SET = {"hospital", "school", "fire_station", "police"}
COMMERCIAL_SET = {"industrial", "store", "shop", "supermarket", "office"}

def classify_poi(props: dict) -> str:
    keys = ["amenity","shop","office","landuse","category","type","poi_class","kind"]
    vals = []
    for k in keys:
        v = props.get(k)
        if isinstance(v, str):
            vals.append(v.strip().lower())
    for v in vals:
        if v in CRITICAL_SET:
            return "CRITICAL"
        if v in COMMERCIAL_SET:
            return "COMMERCIAL"
    if any(v in ("clinic","university","college","kindergarten") for v in vals):
        return "CRITICAL"
    if any(v in ("mall","marketplace","warehouse","factory","plant") for v in vals):
        return "COMMERCIAL"
    return "OTHER"

def weight_for_category(cat: str, weights: Dict[str, float]) -> float:
    return float(weights.get(cat, {"CRITICAL":5.0,"COMMERCIAL":3.0,"OTHER":1.0}.get(cat, 1.0)))
