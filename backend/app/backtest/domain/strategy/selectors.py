from .base import StrategySpec
from .bull_put import bull_put_strategy
from .bear_call import bear_call_strategy
from .no_trade import no_trade_strategy
from .neutral_broken_wing import neutral_broken_wing_strategy

def select_strategy(iv: float, macro_regime: str) -> StrategySpec:
    if macro_regime == "RISK_ON" and iv < 0.25:
        return bull_put_strategy()
    if macro_regime == "RISK_OFF" and iv > 0.30:
        return bear_call_strategy()
    return neutral_broken_wing_strategy()