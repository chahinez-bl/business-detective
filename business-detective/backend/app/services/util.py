import math
import re
import numpy as np


def sanitize(x):
    """Make any structure strictly JSON-safe (NaN/inf -> None, numpy scalars -> python)."""
    if isinstance(x, dict):
        return {str(k): sanitize(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [sanitize(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        f = float(x)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if hasattr(x, "isoformat"):
        return x.isoformat()
    return x


def safe_filename(name: str | None) -> str:
    base = re.split(r"[\\/]", name or "upload")[-1]
    base = re.sub(r"[^\w.\- ]", "_", base, flags=re.UNICODE).strip(" .")
    return (base or "upload")[:100]
