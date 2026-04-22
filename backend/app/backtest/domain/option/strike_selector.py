from __future__ import annotations

from app.backtest.domain.option.pricing import OptionState, black_scholes_greeks


def find_strike_by_delta(
    S: float,
    T: float,
    r: float,
    q: float,
    sigma: float,
    target_delta: float,
    option_type: str,
    tolerance: float = 1e-4,
    max_iter: int = 100,
) -> float:
    """
    Trova lo strike K tale che |delta(K)| = target_delta tramite bisection.

    target_delta: valore assoluto del delta desiderato (es. 0.16 per short, 0.05 per long)
    option_type: "call" | "put"

    Per una put OTM: delta è negativo, si cerca K < S.
    Per una call OTM: delta è positivo, si cerca K > S.

    Raises:
        ValueError: se la bisection non converge o il target delta è fuori range.
    """
    if target_delta <= 0 or target_delta >= 1:
        raise ValueError(f"target_delta deve essere in (0, 1), ricevuto {target_delta}")

    def _abs_delta(K: float) -> float:
        state = OptionState(
            option_type=option_type,
            S=S, K=K, T=T, r=r, sigma=sigma, q=q,
        )
        return abs(black_scholes_greeks(state).delta)

    if option_type == "put":
        lo, hi = S * 0.50, S * 0.9999
    elif option_type == "call":
        lo, hi = S * 1.0001, S * 1.50
    else:
        raise ValueError(f"option_type deve essere 'call' o 'put', ricevuto '{option_type}'")

    delta_lo = _abs_delta(lo)
    delta_hi = _abs_delta(hi)

    if target_delta < min(delta_lo, delta_hi) or target_delta > max(delta_lo, delta_hi):
        raise ValueError(
            f"target_delta {target_delta:.3f} fuori dal range raggiungibile "
            f"[{min(delta_lo, delta_hi):.3f}, {max(delta_lo, delta_hi):.3f}] "
            f"per {option_type} con S={S}, IV={sigma:.2%}, DTE={T*365:.0f}"
        )

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        delta_mid = _abs_delta(mid)

        if abs(delta_mid - target_delta) < tolerance:
            return round(mid, 2)

        # Per una put: |delta| cresce avvicinandosi ad ATM (K → S)
        # Per una call: |delta| cresce avvicinandosi ad ATM (K → S)
        # In entrambi i casi: K più vicino a S → |delta| più alto
        if option_type == "put":
            if delta_mid < target_delta:
                lo = mid   # serve uno strike più vicino ad ATM
            else:
                hi = mid
        else:  # call
            if delta_mid < target_delta:
                hi = mid   # serve uno strike più vicino ad ATM
            else:
                lo = mid

    raise ValueError(
        f"find_strike_by_delta non ha convergito dopo {max_iter} iterazioni "
        f"(target={target_delta:.3f}, option_type={option_type})"
    )
