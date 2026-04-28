import numpy as np
from scipy.stats import norm


def calculate_delta(K: float, S: float, sigma: float, T: float, option_type: str) -> float:
    """
    Delta: rate of change of option price with respect to underlying price.

    Range: Call delta [-1, 1], Put delta [-1, 0]
    Interpretation: For 1 point move in underlying, option price moves by delta points.
    """
    if T <= 0:
        if option_type == "call":
            return 1.0 if S > K else 0.0
        else:
            return 0.0 if S > K else -1.0

    if sigma == 0:
        return 1.0 if S > K else 0.0

    d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))

    if option_type == "call":
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1.0


def calculate_gamma(K: float, S: float, sigma: float, T: float) -> float:
    """
    Gamma: rate of change of delta with respect to underlying price.

    Range: [0, +inf] (always positive for both calls and puts)
    Interpretation: For 1 point move, delta changes by gamma points.
    High gamma = delta sensitive to moves, needs rehedging.
    """
    if T <= 0 or sigma == 0:
        return 0.0

    d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))


def calculate_vega(K: float, S: float, sigma: float, T: float) -> float:
    """
    Vega: rate of change of option price with respect to volatility.

    Measured per 1% change in IV (divide by 100 for per-point)
    Range: [0, +inf] (always positive for both calls and puts)
    Interpretation: For 1% IV increase, option price increases by vega points.
    """
    if T <= 0 or sigma == 0:
        return 0.0

    d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    return S * norm.pdf(d1) * np.sqrt(T) / 100.0  # Per 1% IV


def calculate_theta(
    K: float, S: float, sigma: float, T: float, option_type: str, r: float = 0.03
) -> float:
    """
    Theta: rate of change of option price with respect to time decay.

    Measured per 1 day decay
    Range: Negative for long options, positive for short options
    Interpretation: For 1 day pass, option price changes by theta points.
    Theta decay accelerates as expiration approaches.
    """
    if T <= 0:
        return 0.0

    if sigma == 0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
        )
    else:  # put
        theta = (
            -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
        )

    return theta / 365.0  # Per day
