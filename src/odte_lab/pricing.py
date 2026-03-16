from __future__ import annotations

import math


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, tau: float, sigma: float, right: str) -> float:
    right = right.upper()
    if tau <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        intrinsic = max(spot - strike, 0.0) if right == "CALL" else max(strike - spot, 0.0)
        return intrinsic
    vsqrt = sigma * math.sqrt(tau)
    d1 = (math.log(spot / strike) + 0.5 * sigma * sigma * tau) / vsqrt
    d2 = d1 - vsqrt
    if right == "CALL":
        return spot * norm_cdf(d1) - strike * norm_cdf(d2)
    return strike * norm_cdf(-d2) - spot * norm_cdf(-d1)


def bs_delta(spot: float, strike: float, tau: float, sigma: float, right: str) -> float:
    right = right.upper()
    if tau <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        if right == "CALL":
            return 1.0 if spot > strike else 0.0
        return -1.0 if spot < strike else 0.0
    vsqrt = sigma * math.sqrt(tau)
    d1 = (math.log(spot / strike) + 0.5 * sigma * sigma * tau) / vsqrt
    return norm_cdf(d1) if right == "CALL" else norm_cdf(d1) - 1.0


def implied_vol(mid: float, spot: float, strike: float, tau: float, right: str) -> float | None:
    right = right.upper()
    if mid <= 0 or spot <= 0 or strike <= 0 or tau <= 0:
        return None
    intrinsic = max(spot - strike, 0.0) if right == "CALL" else max(strike - spot, 0.0)
    if mid < intrinsic:
        return None

    lo, hi = 1e-4, 8.0
    plo = bs_price(spot, strike, tau, lo, right) - mid
    phi = bs_price(spot, strike, tau, hi, right) - mid
    if plo * phi > 0:
        return None

    for _ in range(60):
        mid_sigma = 0.5 * (lo + hi)
        pm = bs_price(spot, strike, tau, mid_sigma, right) - mid
        if abs(pm) < 1e-6:
            return mid_sigma
        if plo * pm <= 0:
            hi = mid_sigma
            phi = pm
        else:
            lo = mid_sigma
            plo = pm
    return 0.5 * (lo + hi)
