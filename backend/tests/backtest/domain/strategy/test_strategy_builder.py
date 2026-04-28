import pytest
from app.backtest.domain.strategy.strategy_builder import (
    create_bull_put_spread,
    create_bear_call_spread,
    create_put_broken_wing_butterfly,
    create_bull_call_spread,
    create_bear_put_spread,
    create_long_straddle,
    create_long_strangle,
    create_iron_condor,
    create_iron_butterfly,
    create_calendar_spread,
    create_jade_lizard,
    create_reverse_jade_lizard,
    create_diagonal_spread,
)


class TestExistingStrategies:
    """Test existing strategy builders (FASE 0)."""

    def test_bull_put_spread_creates_2_legs(self):
        pos = create_bull_put_spread(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "bull_put_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == -1  # short
        assert pos.legs[1].sign == +1  # long
        assert pos.legs[0].state.option_type == "put"
        assert pos.legs[1].state.option_type == "put"

    def test_bear_call_spread_creates_2_legs(self):
        pos = create_bear_call_spread(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "bear_call_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == -1
        assert pos.legs[1].sign == +1
        assert all(leg.state.option_type == "call" for leg in pos.legs)

    def test_broken_wing_butterfly_creates_4_legs(self):
        pos = create_put_broken_wing_butterfly(
            date="2026-04-28", S=100, iv=0.25, dte_days=45
        )
        assert pos.name == "put_broken_wing_butterfly"
        assert len(pos.legs) == 4


class TestNewStrategies:
    """Test new strategy builders (FASE 1)."""

    def test_bull_call_spread_creates_2_legs(self):
        pos = create_bull_call_spread(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "bull_call_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == +1  # long first
        assert pos.legs[1].sign == -1  # short second
        assert pos.legs[0].state.option_type == "call"
        assert pos.legs[1].state.option_type == "call"
        assert pos.legs[0].state.K < pos.legs[1].state.K  # long OTM, short ITM

    def test_bear_put_spread_creates_2_legs(self):
        pos = create_bear_put_spread(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "bear_put_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == -1  # short first
        assert pos.legs[1].sign == +1  # long second
        assert all(leg.state.option_type == "put" for leg in pos.legs)

    def test_long_straddle_creates_2_long_legs_atm(self):
        pos = create_long_straddle(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "long_straddle"
        assert len(pos.legs) == 2
        assert all(leg.sign == +1 for leg in pos.legs)
        assert pos.legs[0].state.option_type == "call"
        assert pos.legs[1].state.option_type == "put"
        assert pos.legs[0].state.K == pos.legs[1].state.K  # Same strike (ATM)

    def test_long_strangle_creates_2_long_legs_otm(self):
        pos = create_long_strangle(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "long_strangle"
        assert len(pos.legs) == 2
        assert all(leg.sign == +1 for leg in pos.legs)
        assert pos.legs[0].state.option_type == "call"
        assert pos.legs[1].state.option_type == "put"
        # Verify OTM: call_strike > spot, put_strike < spot
        assert pos.legs[0].state.K > 100
        assert pos.legs[1].state.K < 100

    def test_iron_condor_creates_4_legs(self):
        pos = create_iron_condor(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "iron_condor"
        assert len(pos.legs) == 4
        puts = [leg for leg in pos.legs if leg.state.option_type == "put"]
        calls = [leg for leg in pos.legs if leg.state.option_type == "call"]
        assert len(puts) == 2
        assert len(calls) == 2
        # Verify structure: 1 short + 1 long per side
        assert sum(leg.sign for leg in puts) == 0
        assert sum(leg.sign for leg in calls) == 0

    def test_iron_butterfly_creates_4_legs(self):
        pos = create_iron_butterfly(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "iron_butterfly"
        assert len(pos.legs) == 4
        short_legs = [leg for leg in pos.legs if leg.sign == -1]
        long_legs = [leg for leg in pos.legs if leg.sign == +1]
        assert len(short_legs) == 2
        assert len(long_legs) == 2

    def test_calendar_spread_creates_2_legs_diff_dte(self):
        pos = create_calendar_spread(
            date="2026-04-28",
            S=100,
            iv=0.25,
            dte_days_near=30,
            dte_days_far=60,
        )
        assert pos.name == "calendar_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == -1  # short near
        assert pos.legs[1].sign == +1  # long far
        assert pos.legs[0].state.K == pos.legs[1].state.K  # Same strike
        assert pos.legs[0].state.T < pos.legs[1].state.T  # Near < Far

    def test_jade_lizard_creates_3_legs(self):
        pos = create_jade_lizard(date="2026-04-28", S=100, iv=0.25, dte_days=45)
        assert pos.name == "jade_lizard"
        assert len(pos.legs) == 3
        assert sum(leg.sign for leg in pos.legs) == -1  # Net short

    def test_reverse_jade_lizard_creates_3_legs(self):
        pos = create_reverse_jade_lizard(
            date="2026-04-28", S=100, iv=0.25, dte_days=45
        )
        assert pos.name == "reverse_jade_lizard"
        assert len(pos.legs) == 3
        assert sum(leg.sign for leg in pos.legs) == -1  # Net short

    def test_diagonal_spread_creates_2_legs_diff_strike_dte(self):
        pos = create_diagonal_spread(
            date="2026-04-28",
            S=100,
            iv=0.25,
            dte_days_near=30,
            dte_days_far=60,
        )
        assert pos.name == "diagonal_spread"
        assert len(pos.legs) == 2
        assert pos.legs[0].sign == -1  # short near
        assert pos.legs[1].sign == +1  # long far
        assert pos.legs[0].state.K != pos.legs[1].state.K  # Different strikes
        assert pos.legs[0].state.T < pos.legs[1].state.T  # Different DTE


class TestPositionProperties:
    """Test common position properties across all strategies."""

    def test_all_positions_have_valid_dates(self):
        date = "2026-04-28"
        strategies = [
            create_bull_call_spread,
            create_bear_put_spread,
            create_long_straddle,
            create_long_strangle,
            create_iron_condor,
            create_iron_butterfly,
            create_jade_lizard,
            create_reverse_jade_lizard,
        ]
        for strategy_fn in strategies:
            pos = strategy_fn(date=date, S=100, iv=0.25, dte_days=45)
            assert pos.opened_at == date

    def test_all_positions_have_option_legs(self):
        strategies = [
            create_bull_call_spread,
            create_bear_put_spread,
            create_long_straddle,
            create_long_strangle,
            create_iron_condor,
            create_iron_butterfly,
            create_jade_lizard,
            create_reverse_jade_lizard,
        ]
        for strategy_fn in strategies:
            pos = strategy_fn(date="2026-04-28", S=100, iv=0.25, dte_days=45)
            assert all(leg.state is not None for leg in pos.legs)
            assert all(leg.state.option_type in ["call", "put"] for leg in pos.legs)

    def test_all_positions_have_quantity(self):
        strategies = [
            create_bull_call_spread,
            create_bear_put_spread,
            create_long_straddle,
        ]
        for strategy_fn in strategies:
            pos = strategy_fn(date="2026-04-28", S=100, iv=0.25, dte_days=45, quantity=5)
            assert all(leg.quantity == 5 for leg in pos.legs)
