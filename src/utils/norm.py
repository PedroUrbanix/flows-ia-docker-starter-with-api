
def q5_q95(values):
    xs = [v for v in values if v is not None]
    if not xs: return (0.0, 1.0)
    xs = sorted(xs)
    def q(p):
        if not xs: return 0.0
        k = (len(xs)-1) * p
        f = int(k); c = min(f+1, len(xs)-1)
        if f == c: return xs[f]
        return xs[f] + (xs[c]-xs[f])*(k-f)
    return (q(0.05), q(0.95))

def norm_direct(x, p5, p95):
    if x is None: return 0.0
    if p95 <= p5: return 0.0
    v = (x - p5) / (p95 - p5)
    if v < 0: v = 0.0
    if v > 1: v = 1.0
    return float(v)

def norm_inverse(x, p5, p95):
    if x is None: return 0.0
    if p95 <= p5: return 0.0
    v = (p95 - x) / (p95 - p5)
    if v < 0: v = 0.0
    if v > 1: v = 1.0
    return float(v)
