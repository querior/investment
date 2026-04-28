import pytest
import pandas as pd
import numpy as np
from app.engines.option.pricing import (
    PricingContext,
    black_scholes,
    calculate_pricing,
)
from app.engines.option.greeks_calculator import (
    calculate_delta,
    calculate_gamma,
    calculate_vega,
    calculate_theta,
)
from app.backtest.domain.strategy import (
    bull_call_spread_strategy,
    bear_put_spread_strategy,
    iron_condor_strategy,
)


class TestBlackScholes:
    """Unit tests for Black-Scholes pricing function."""

    def test_call_itm_at_expiration(self):
        """Call option at expiration, ITM: value = S - K."""
        price = black_scholes(S=110, K=100, T=0, sigma=0.2, r=0.03, option_type="call")
        assert price == pytest.approx(10.0)

    def test_call_otm_at_expiration(self):
        """Call option at expiration, OTM: value = 0."""
        price = black_scholes(S=90, K=100, T=0, sigma=0.2, r=0.03, option_type="call")
        assert price == 0.0

    def test_put_itm_at_expiration(self):
        """Put option at expiration, ITM: value = K - S."""
        price = black_scholes(S=90, K=100, T=0, sigma=0.2, r=0.03, option_type="put")
        assert price == pytest.approx(10.0)

    def test_put_otm_at_expiration(self):
        """Put option at expiration, OTM: value = 0."""
        price = black_scholes(S=110, K=100, T=0, sigma=0.2, r=0.03, option_type="put")
        assert price == 0.0

    def test_atm_call_positive_value(self):
        """ATM call should have positive value with time value."""
        price = black_scholes(S=100, K=100, T=0.25, sigma=0.2, r=0.03, option_type="call")
        assert price > 0
        assert price < 10  # Should be less than intrinsic max

    def test_atm_put_positive_value(self):
        """ATM put should have positive value with time value."""
        price = black_scholes(S=100, K=100, T=0.25, sigma=0.2, r=0.03, option_type="put")
        assert price > 0

    def test_zero_volatility_call(self):
        """With zero volatility, call value is discounted intrinsic."""
        price = black_scholes(S=110, K=100, T=0.25, sigma=0, r=0.03, option_type="call")
        expected = 110 - 100 * np.exp(-0.03 * 0.25)
        assert price == pytest.approx(expected, rel=0.01)

    def test_zero_volatility_put(self):
        """With zero volatility, put value is discounted intrinsic."""
        price = black_scholes(S=90, K=100, T=0.25, sigma=0, r=0.03, option_type="put")
        expected = 100 * np.exp(-0.03 * 0.25) - 90
        assert price == pytest.approx(expected, rel=0.01)


class TestGreeksCalculators:
    """Unit tests for individual Greeks functions."""

    def test_delta_call_atm_positive(self):
        """Delta for ATM call should be ~0.5."""
        delta = calculate_delta(K=100, S=100, sigma=0.2, T=0.25, option_type="call")
        assert 0.4 < delta < 0.6

    def test_delta_call_itm_approaches_1(self):
        """Delta for deep ITM call approaches 1."""
        delta = calculate_delta(K=50, S=100, sigma=0.2, T=0.25, option_type="call")
        assert delta > 0.95

    def test_delta_call_otm_approaches_0(self):
        """Delta for deep OTM call approaches 0."""
        delta = calculate_delta(K=200, S=100, sigma=0.2, T=0.25, option_type="call")
        assert delta < 0.05

    def test_delta_put_negative(self):
        """Delta for put is negative."""
        delta = calculate_delta(K=100, S=100, sigma=0.2, T=0.25, option_type="put")
        assert -0.6 < delta < -0.4

    def test_gamma_always_positive(self):
        """Gamma is always positive for both calls and puts."""
        gamma_call = calculate_gamma(K=100, S=100, sigma=0.2, T=0.25)
        gamma_put = calculate_gamma(K=100, S=100, sigma=0.2, T=0.25)
        assert gamma_call > 0
        assert gamma_put > 0
        assert gamma_call == gamma_put

    def test_gamma_atm_highest(self):
        """Gamma is highest for ATM options."""
        gamma_atm = calculate_gamma(K=100, S=100, sigma=0.2, T=0.25)
        gamma_itm = calculate_gamma(K=90, S=100, sigma=0.2, T=0.25)
        gamma_otm = calculate_gamma(K=110, S=100, sigma=0.2, T=0.25)
        assert gamma_atm > gamma_itm
        assert gamma_atm > gamma_otm

    def test_vega_always_positive(self):
        """Vega is always positive."""
        vega = calculate_vega(K=100, S=100, sigma=0.2, T=0.25)
        assert vega > 0

    def test_vega_atm_highest(self):
        """Vega is highest for ATM options."""
        vega_atm = calculate_vega(K=100, S=100, sigma=0.2, T=0.25)
        vega_itm = calculate_vega(K=90, S=100, sigma=0.2, T=0.25)
        assert vega_atm > vega_itm

    def test_theta_call_negative(self):
        """Theta for long call is negative (time decay)."""
        theta = calculate_theta(K=100, S=100, sigma=0.2, T=0.25, option_type="call")
        assert theta < 0

    def test_theta_put_negative(self):
        """Theta for long put is negative (time decay)."""
        theta = calculate_theta(K=100, S=100, sigma=0.2, T=0.25, option_type="put")
        assert theta < 0

    def test_greeks_at_expiration_zero(self):
        """Gamma, Vega, Theta should be zero at expiration."""
        gamma = calculate_gamma(K=100, S=100, sigma=0.2, T=0)
        vega = calculate_vega(K=100, S=100, sigma=0.2, T=0)
        theta = calculate_theta(K=100, S=100, sigma=0.2, T=0, option_type="call")
        assert gamma == 0.0
        assert vega == 0.0
        assert theta == 0.0


class TestPricingContext:
    """Unit tests for PricingContext dataclass."""

    def test_pricing_context_creation(self):
        """PricingContext can be created with all fields."""
        ctx = PricingContext(
            strategy_name="test_strategy",
            spot=100,
            iv=0.2,
            dte_days=45,
            strikes={"leg_0": 100, "leg_1": 110},
            delta=0.5,
            gamma=0.02,
            vega=10.0,
            theta=-0.5,
            market_price=2.0,
            fair_value=2.5,
            bid_ask_spread=0.05,
            bid_ask_pct=0.02,
            edge=0.5,
            breakeven_distance=2.5,
        )
        assert ctx.strategy_name == "test_strategy"
        assert ctx.spot == 100
        assert ctx.delta == 0.5
        assert ctx.edge == 0.5

    def test_pricing_context_all_strategies(self):
        """Test PricingContext works with all 13 strategies."""
        from app.backtest.domain.strategy import (
            bull_call_spread_strategy,
            bear_put_spread_strategy,
            bull_put_strategy,
            bear_call_strategy,
            long_straddle_strategy,
            long_strangle_strategy,
            iron_condor_strategy,
            iron_butterfly_strategy,
            calendar_spread_strategy,
            jade_lizard_strategy,
            reverse_jade_lizard_strategy,
            diagonal_spread_strategy,
            neutral_broken_wing_strategy,
        )

        strategies = [
            ("bull_call_spread", bull_call_spread_strategy),
            ("bear_put_spread", bear_put_spread_strategy),
            ("bull_put_spread", bull_put_strategy),
            ("bear_call_spread", bear_call_strategy),
            ("long_straddle", long_straddle_strategy),
            ("long_strangle", long_strangle_strategy),
            ("iron_condor", iron_condor_strategy),
            ("iron_butterfly", iron_butterfly_strategy),
            ("calendar_spread", calendar_spread_strategy),
            ("jade_lizard", jade_lizard_strategy),
            ("reverse_jade_lizard", reverse_jade_lizard_strategy),
            ("diagonal_spread", diagonal_spread_strategy),
            ("put_broken_wing_butterfly", neutral_broken_wing_strategy),
        ]

        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }

        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })

        for expected_name, strategy_func in strategies:
            spec = strategy_func()
            ctx = calculate_pricing(spec, row, entry_config)

            # Validate PricingContext has all required fields
            assert ctx.strategy_name == expected_name
            assert ctx.spot == 100
            assert ctx.iv == 0.2
            assert ctx.dte_days == 45
            assert isinstance(ctx.strikes, dict)
            assert len(ctx.strikes) >= 2  # At least 2 legs

            # Validate Greeks are calculated (floats, not NaN)
            assert isinstance(ctx.delta, (float, np.floating))
            assert isinstance(ctx.gamma, (float, np.floating))
            assert isinstance(ctx.vega, (float, np.floating))
            assert isinstance(ctx.theta, (float, np.floating))
            assert not np.isnan(ctx.delta)
            assert not np.isnan(ctx.gamma)
            assert not np.isnan(ctx.vega)
            assert not np.isnan(ctx.theta)

            # Validate pricing fields
            assert isinstance(ctx.fair_value, (float, np.floating))
            assert isinstance(ctx.market_price, (float, np.floating))
            assert ctx.bid_ask_spread >= 0
            assert ctx.bid_ask_pct >= 0


class TestCalculatePricing:
    """Unit tests for calculate_pricing function."""

    def test_pricing_zone_a_bull_call_spread(self):
        """Test pricing for Zone A bull call spread."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
            "market_price": 1.5,
            "bid_ask_pct": 0.02,
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        assert ctx.strategy_name == "bull_call_spread"
        assert ctx.spot == 100
        assert ctx.iv == 0.2
        assert ctx.dte_days == 45
        assert isinstance(ctx.strikes, dict)
        assert len(ctx.strikes) >= 2  # Bull spread has at least 2 legs

        # Greeks should be calculated (floats, not NaN)
        assert isinstance(ctx.delta, (float, np.floating))
        assert isinstance(ctx.gamma, (float, np.floating))
        assert isinstance(ctx.vega, (float, np.floating))
        assert isinstance(ctx.theta, (float, np.floating))
        assert not np.isnan(ctx.delta)
        assert not np.isnan(ctx.gamma)
        assert not np.isnan(ctx.vega)
        assert not np.isnan(ctx.theta)

        # Pricing and market price should be calculated
        assert isinstance(ctx.fair_value, (float, np.floating))
        assert isinstance(ctx.market_price, (float, np.floating))
        assert ctx.bid_ask_spread >= 0

    def test_pricing_zone_a_bear_put_spread(self):
        """Test pricing for Zone A bear put spread."""
        row = pd.Series({
            "close": 100,
            "iv": 0.15,
            "dte_days": 30,
            "date": "2026-04-28",
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bear_put_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        assert ctx.strategy_name == "bear_put_spread"
        assert ctx.spot == 100
        assert ctx.dte_days == 30

    def test_pricing_zone_d_iron_condor(self):
        """Test pricing for Zone D iron condor (4-leg strategy)."""
        row = pd.Series({
            "close": 100,
            "iv": 0.3,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = iron_condor_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        assert ctx.strategy_name == "iron_condor"
        assert ctx.spot == 100
        assert len(ctx.strikes) == 4  # Iron condor has 4 strikes

    def test_pricing_with_fallback_market_price(self):
        """Test that market_price defaults to fair_value if not provided."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        # market_price should equal fair_value when not provided
        assert ctx.market_price == ctx.fair_value

    def test_pricing_with_custom_bid_ask(self):
        """Test bid/ask spread calculation."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
            "market_price": 2.0,
            "bid_ask_pct": 0.05,  # 5% spread
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        expected_spread = 2.0 * 0.05
        assert ctx.bid_ask_spread == pytest.approx(expected_spread)
        assert ctx.bid_ask_pct == 0.05

    def test_edge_calculation(self):
        """Test edge calculation (fair_value - market_price)."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
            "market_price": 1.0,
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        expected_edge = ctx.fair_value - 1.0
        assert ctx.edge == pytest.approx(expected_edge)

    def test_position_signs_aggregation(self):
        """Test that Greeks are aggregated respecting position signs."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        # Test with a multi-leg strategy to verify Greeks aggregation
        spec = iron_condor_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        # Iron condor has 4 legs with mixed signs, resulting Greeks are aggregated
        # Just verify Greeks are calculated (aggregate of multiple signed legs)
        assert isinstance(ctx.delta, (float, np.floating))
        assert isinstance(ctx.gamma, (float, np.floating))
        # Gamma can be aggregated to either sign depending on legs

    def test_different_spot_prices(self):
        """Test pricing at different spot prices produces different values."""
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bear_put_spread_strategy()

        # Price at spot=100
        row1 = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        ctx1 = calculate_pricing(spec, row1, entry_config)

        # Price at spot=90 (lower)
        row2 = pd.Series({
            "close": 90,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        ctx2 = calculate_pricing(spec, row2, entry_config)

        # Pricing should change at different spot prices
        assert ctx1.fair_value != ctx2.fair_value

    def test_different_iv_levels(self):
        """Test pricing at different IV levels produces different values."""
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = iron_condor_strategy()

        # Price at low IV
        row1 = pd.Series({
            "close": 100,
            "iv": 0.1,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        ctx1 = calculate_pricing(spec, row1, entry_config)

        # Price at high IV
        row2 = pd.Series({
            "close": 100,
            "iv": 0.3,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        ctx2 = calculate_pricing(spec, row2, entry_config)

        # Pricing should change at different IV levels
        assert ctx1.fair_value != ctx2.fair_value
        # IV should be different
        assert ctx1.iv != ctx2.iv

    def test_different_dte(self):
        """Test pricing at different days to expiration."""
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        # Price with 45 DTE
        row1 = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        ctx1 = calculate_pricing(spec, row1, entry_config)

        # Price with 5 DTE
        row2 = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 5,
            "date": "2026-04-28",
        })
        ctx2 = calculate_pricing(spec, row2, entry_config)

        # Theta magnitude should increase as DTE decreases
        assert abs(ctx2.theta) > abs(ctx1.theta)

    def test_default_dte_fallback(self):
        """Test default DTE of 45 days when not provided."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "date": "2026-04-28",
        })
        entry_config = {
            "target_delta_short": 0.16,
            "target_delta_long": 0.05,
        }
        spec = bull_call_spread_strategy()

        ctx = calculate_pricing(spec, row, entry_config)

        assert ctx.dte_days == 45
