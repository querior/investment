from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostModel:
    commission_per_contract: float
    min_commission: float
    bid_ask_spread_pct: float

    def total_cost(self, premium: float, n_contracts: int) -> float:
        commission = max(
            n_contracts * self.commission_per_contract,
            self.min_commission,
        )
        slippage = abs(premium) * self.bid_ask_spread_pct
        return commission + slippage

    def fill_price(self, mid_price: float, side: str) -> float:
        """Simula fill realistico: short → fill al bid, long → fill all'ask."""
        half_spread = mid_price * (self.bid_ask_spread_pct / 2)
        if side == "short":
            return mid_price - half_spread
        return mid_price + half_spread


@dataclass
class InstrumentConfig:
    ticker: str
    dividend_yield: float
    iv_alpha: float
    cost_model: CostModel
    contract_multiplier: int = 100
    settlement: str = "physical"
    iv_min: float = 0.10
    iv_max: float = 0.80

    @staticmethod
    def from_db(record) -> "InstrumentConfig":
        return InstrumentConfig(
            ticker=record.ticker,
            dividend_yield=record.dividend_yield,
            iv_alpha=record.iv_alpha,
            cost_model=CostModel(
                commission_per_contract=record.commission_per_contract,
                min_commission=record.min_commission,
                bid_ask_spread_pct=record.bid_ask_spread_pct,
            ),
            contract_multiplier=record.contract_multiplier,
            settlement=record.settlement,
            iv_min=record.iv_min,
            iv_max=record.iv_max,
        )
