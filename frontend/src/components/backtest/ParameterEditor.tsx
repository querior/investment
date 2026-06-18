import { useState, useMemo } from "react";
import {
	Button,
	Card,
	Collapse,
	Divider,
	Form,
	Input,
	InputNumber,
	Select,
	Switch,
	Tag,
	Tabs,
	Tooltip,
} from "antd";
import {
	CheckOutlined,
	CloseOutlined,
	EditOutlined,
	QuestionCircleOutlined,
	SettingOutlined,
	InfoCircleOutlined,
} from "@ant-design/icons";
import type {
	BacktestRunDto,
	BacktestConfigDto,
} from "../../features/backtest/types";
import { getStrategyMeta } from "../../utils/strategy";

interface ParameterEditorProps {
	currentRun: BacktestRunDto;
	backtestConfig: BacktestConfigDto | null;
	onSave: (parameters: Record<string, string>) => void;
	onCancel: () => void;
	onEdit?: () => void;
	loading?: boolean;
	readOnly?: boolean;
}

interface ParameterSchema {
	type: string;
	min?: number;
	max?: number;
	default?: string;
	unit?: string;
}

interface ParameterValue {
	value: string | number | boolean;
	unit?: string;
}

type ParamDraft = Record<string, string | number | boolean>;

const PARAMETER_HINTS: Record<string, { label: string; description: string }> =
	{
		// Header
		symbol: {
			label: "Symbol",
			description: "Ticker symbol (IWM, SPY, QQQ, SPX)",
		},
		initial_capital: {
			label: "Initial Capital",
			description: "Starting portfolio value",
		},

		// Entry
		"entry.iv_min_threshold": {
			label: "IV Minimum Threshold",
			description:
				"Minimum IV to open any position. Filters out very low premium trades.",
		},
		"entry.rsi_min_bull": {
			label: "RSI Minimum (Bull Put)",
			description:
				"Minimum RSI (0-100) to open bull put spread. Avoids oversold entries.",
		},
		"entry.iv_min_neutral": {
			label: "IV Minimum (Neutral)",
			description:
				"Minimum IV for neutral strategies. Higher threshold protects against low premium.",
		},
		"entry.iv_rv_ratio_min": {
			label: "IV/RV Ratio Minimum",
			description:
				"Minimum ratio of implied to realized volatility. Ensures IV premium exists.",
		},

		// Exit - DTE
		"exit.rule_dte.enabled": {
			label: "Enable DTE Rule",
			description: "Close positions when days to expiration reaches threshold.",
		},
		"exit.rule_dte.threshold_days": {
			label: "DTE Threshold (days)",
			description:
				"Close position when DTE falls below this value (e.g., 21 days).",
		},

		// Exit - Profit Target
		"exit.rule_profit_target.enabled": {
			label: "Enable Profit Target",
			description: "Close position when profit reaches target percentage.",
		},
		"exit.rule_profit_target.threshold_pct": {
			label: "Profit Target %",
			description:
				"Close when profit reaches this % of initial credit. Typical: 50%.",
		},

		// Exit - Stop Loss
		"exit.rule_stop_loss.enabled": {
			label: "Enable Stop Loss",
			description: "Close position when loss exceeds threshold.",
		},
		"exit.rule_stop_loss.threshold_pct": {
			label: "Stop Loss %",
			description:
				"Close when loss exceeds this % of initial credit. Typical: 150-200%.",
		},

		// Exit - Trailing Stop
		"exit.rule_trailing_stop.enabled": {
			label: "Enable Trailing Stop",
			description:
				"Close when profit drops below threshold after reaching profit target.",
		},
		"exit.rule_trailing_stop.min_profit_pct": {
			label: "Min Profit for Trailing %",
			description: "Start trailing stop when profit reaches this %.",
		},
		"exit.rule_trailing_stop.pullback_pct": {
			label: "Trailing Pullback %",
			description:
				"Close if profit drops below this % from the maximum profit reached.",
		},

		// Exit - Macro Reversal
		"exit.rule_macro_reversal.enabled": {
			label: "Enable Macro Reversal Exit",
			description:
				"Close position if macro regime reverses (e.g., RISK_ON → RISK_OFF).",
		},

		// Exit - Momentum Reversal
		"exit.rule_momentum_reversal.enabled": {
			label: "Enable Momentum Reversal Exit",
			description:
				"Close position if technical momentum reverses (RSI + MACD).",
		},
		"exit.rule_momentum_reversal.rsi_threshold": {
			label: "RSI Threshold for Exit",
			description:
				"Close if RSI crosses below threshold (e.g., 30 = oversold).",
		},

		// Exit - IV Spike
		"exit.rule_iv_spike.enabled": {
			label: "Enable IV Spike Exit",
			description: "Close position if IV spikes significantly.",
		},
		"exit.rule_iv_spike.threshold_ratio": {
			label: "IV Spike Ratio",
			description:
				"Close if IV/rolling_avg exceeds this ratio (e.g., 2.0 = 2x volatility).",
		},

		// Exit - Delta Breach
		"exit.rule_delta_breach.enabled": {
			label: "Enable Delta Breach Exit",
			description: "Close position if delta breaches risk threshold.",
		},
		"exit.rule_delta_breach.threshold": {
			label: "Delta Breach Threshold",
			description: "Close if absolute delta exceeds this value (0-1 range).",
		},

		// Exit - Theta Decay
		"exit.rule_theta_decay.enabled": {
			label: "Enable Theta Decay Exit",
			description: "Close position if theta decay rate drops below threshold.",
		},
		"exit.rule_theta_decay.threshold_ratio": {
			label: "Theta Decay Ratio",
			description: "Close if theta/initial_theta drops below this ratio.",
		},

		// Strategy
		"strategy.initial_allocation": {
			label: "Initial Allocation",
			description:
				"Start with neutral weights or first computed target allocation.",
		},
		"strategy.coherence_factor": {
			label: "Coherence Factor",
			description:
				"Weight for coherence in allocation engine (0-1). Higher = stricter allocation.",
		},
		"strategy.allocation_alpha": {
			label: "Allocation Alpha",
			description:
				"EWM smoothing factor for allocation changes (0-1). Lower = smoother transitions.",
		},

		// Risk
		max_risk: {
			label: "Max Risk",
			description: "Maximum allowed risk per trade (percentage).",
		},

		// Entry - Strike Delta
		"entry.cooldown_days": {
			label: "Cooldown After Close (days)",
			description:
				"Minimum days before reopening the same strategy after it closes. Prevents rapid open/close cycles.",
		},

		// Entry Scoring - Weights
		"entry_score.w1_iv_rank": {
			label: "Weight: IV Rank",
			description:
				"Weight for IV Rank component in entry score (0-1). Normalized with other weights.",
		},
		"entry_score.w2_iv_hv": {
			label: "Weight: IV/HV Ratio",
			description: "Weight for IV/HV ratio component in entry score (0-1).",
		},
		"entry_score.w3_squeeze": {
			label: "Weight: Squeeze Intensity",
			description: "Weight for TTM Squeeze component in entry score (0-1).",
		},
		"entry_score.w4_rsi": {
			label: "Weight: RSI Neutrality",
			description: "Weight for RSI neutrality component in entry score (0-1).",
		},
		"entry_score.w5_dte": {
			label: "Weight: DTE Score",
			description:
				"Weight for Days to Expiration component in entry score (0-1).",
		},
		"entry_score.w6_volume": {
			label: "Weight: Volume Ratio",
			description: "Weight for volume ratio component in entry score (0-1).",
		},
		"entry_score.w7_term_structure": {
			label: "Weight: IV Term Structure",
			description:
				"Weight for IV term slope direction (VIXCLS/VXVCLS delta). Negative delta = stress resolving = higher score.",
		},
		"entry_score.w8_credit_spread": {
			label: "Weight: Credit Spread",
			description:
				"Weight for BAA10Y 5-day delta. Tightening spread = stress resolving = higher score.",
		},
		"entry_score.w9_vvix": {
			label: "Weight: VVIX Rank",
			description:
				"Weight for VVIX 252-day percentile rank. Lower rank = calmer IV uncertainty = higher score.",
		},

		// Entry Sizing
		"entry_size.threshold_full": {
			label: "Score Threshold (Full Size)",
			description:
				"Entry score threshold for full position sizing (0-100). Score >= this = 100% size.",
		},
		"entry_size.threshold_reduced": {
			label: "Score Threshold (Reduced Size)",
			description:
				"Entry score threshold for reduced position sizing (0-100). Score >= this = 75% size, below = no entry.",
		},
		"entry_size.multiplier_full": {
			label: "Size Multiplier (Full)",
			description:
				"Position size multiplier when score > threshold_full (0-1). 1.0 = 100% of nominal size.",
		},
		"entry_size.multiplier_reduced": {
			label: "Size Multiplier (Reduced)",
			description:
				"Position size multiplier when score >= threshold_reduced (0-1). 0.75 = 75% of nominal size.",
		},

		// Entry Scoring - DTE
		"entry_score.dte_min": {
			label: "DTE Minimum (days)",
			description:
				"Minimum days to expiration threshold. Below this = unfavorable timing.",
		},
		"entry_score.dte_optimal_min": {
			label: "DTE Optimal Min (days)",
			description:
				"Start of optimal DTE range (days). Ideal entry between optimal_min and optimal_max.",
		},
		"entry_score.dte_optimal_max": {
			label: "DTE Optimal Max (days)",
			description:
				"End of optimal DTE range (days). Typical: 35-45 for weekly strategies.",
		},
		"entry_score.dte_max": {
			label: "DTE Maximum (days)",
			description:
				"Maximum days to expiration threshold. Above this = less theta decay.",
		},

		// Entry Scoring - RSI Neutrality
		"entry_score.rsi_neutral_min": {
			label: "RSI Neutral Min",
			description:
				"Lower bound of RSI neutral zone (0-100). Typical: 40. Inside [40,60] = perfect momentum.",
		},
		"entry_score.rsi_neutral_max": {
			label: "RSI Neutral Max",
			description:
				"Upper bound of RSI neutral zone (0-100). Typical: 60. Inside [40,60] = perfect momentum.",
		},

		// Pipeline - IV Rank
		"iv_rank.lookback_days": {
			label: "IV Rank Lookback (days)",
			description:
				"Rolling window for IV Rank calculation (days). 252 = annual percentile rank.",
		},

		// Pipeline - ADX
		"adx.period": {
			label: "ADX Period",
			description:
				"Period for Average Directional Index calculation. 14 = standard, higher = smoother.",
		},

		// Pipeline - Squeeze
		"squeeze.bb_percentile": {
			label: "BB Percentile (Squeeze)",
			description:
				"Bollinger Band width percentile threshold for squeeze detection (0-50). Lower % = tighter squeeze.",
		},
		"squeeze.macd_threshold": {
			label: "MACD Threshold (Squeeze)",
			description:
				"MACD absolute value threshold for flatness detection. Lower = stricter squeeze signal.",
		},

		// Pipeline - Volume
		"volume.sma_period": {
			label: "Volume SMA Period (days)",
			description:
				"Period for volume simple moving average. Used for volume_ratio calculation.",
		},

		// Pipeline - Volatility Bounds
		alpha_volatility: {
			label: "Alpha Volatility",
			description:
				"Scaling factor for volatility-based position sizing. Higher = more size in high vol.",
		},
		iv_min: {
			label: "IV Minimum",
			description:
				"Absolute minimum IV threshold for any entry (0-1). Filters out ultra-low premium.",
		},
		iv_max: {
			label: "IV Maximum",
			description:
				"Absolute maximum IV threshold for any entry (0-2). Filters out excessive premium.",
		},

		// Debug
		"debug.force_open": {
			label: "Force Open",
			description:
				"Bypassa il threshold L5 e apre ogni candidato valido. Modalità raccomandata fino alla ricalibratura dei pesi opportunity score (Sprint 3). Con false, L5 tende a filtrare le credit strategies per bias strutturale nel R/R score.",
		},

		// Rollout
		"rollout.enabled": {
			label: "Enable Rollout",
			description:
				"When a position exits via DTE rule, reopen the same strategy on the next expiration instead of waiting for the next entry signal.",
		},
		"rollout.min_profit_pct": {
			label: "Min Profit to Roll (%)",
			description:
				"Only roll positions that closed with a profit >= X% of initial credit. 0 = always roll.",
		},

		// Portfolio Trailing Stop
		"exit.portfolio_trailing_stop.enabled": {
			label: "Enable Portfolio Trailing Stop",
			description:
				"Close all open positions if portfolio equity drops more than X% below its peak. Operates at portfolio level, independently of per-position rules.",
		},
		"exit.portfolio_trailing_stop.pullback_pct": {
			label: "Portfolio Pullback %",
			description:
				"Maximum allowed drawdown from peak equity before all positions are closed. E.g. 20 = close everything if equity falls 20% below the high-water mark.",
		},

		// Cost Model (IBKR commissions)
		"cost_model.commission_per_contract": {
			label: "Commission per Contract",
			description:
				"IBKR fee per option contract per leg ($). Default: $0.65 (IBKR Fixed pricing).",
		},
		"cost_model.min_commission": {
			label: "Min Commission per Order",
			description:
				"Minimum commission per order ($). Default: $1.00 (IBKR Fixed pricing).",
		},

		// Execution
		entry_every_n_days: {
			label: "Entry Every N Days",
			description:
				"Frequency of entry signals (days). 30 = check for new entries every 30 days.",
		},
		ticker: {
			label: "Ticker",
			description: "Underlying ticker symbol (IWM, SPY, QQQ, etc.).",
		},

		// Decision Layer - Thresholds
		"decision.threshold_open": {
			label: "Decision Score Threshold (Open)",
			description:
				"Minimum composite opportunity score (0-100) to OPEN a position. Typical: 75. Below = no trade.",
		},
		"decision.threshold_monitor": {
			label: "Decision Score Threshold (Monitor)",
			description:
				"Opportunity score threshold (0-100) for MONITOR status. Between this and threshold_open = borderline, worth monitoring.",
		},
		"decision.max_bid_ask_pct": {
			label: "Max Bid/Ask Spread %",
			description:
				"Maximum tolerable bid/ask spread as % of mark price. Higher spread = lower execution quality. Typical: 15%.",
		},

		// Decision Layer - Opportunity Scoring Weights
		"opportunity.weight_edge": {
			label: "Weight: Pricing Edge",
			description:
				"Weight for pricing edge dimension (fair value vs market) in opportunity score (0-1). Typical: 0.35 (highest priority).",
		},
		"opportunity.weight_rr": {
			label: "Weight: Risk/Reward",
			description:
				"Weight for risk/reward ratio dimension (max gain vs max loss) in opportunity score (0-1). Typical: 0.25.",
		},
		"opportunity.weight_bep": {
			label: "Weight: Breakeven Reachability",
			description:
				"Weight for breakeven reachability dimension (distance to BEP in sigmas) in opportunity score (0-1). Typical: 0.20.",
		},
		"opportunity.weight_execution": {
			label: "Weight: Execution Cost",
			description:
				"Weight for execution cost dimension (bid/ask impact) in opportunity score (0-1). Typical: 0.15.",
		},
		"opportunity.weight_efficiency": {
			label: "Weight: Capital Efficiency",
			description:
				"Weight for capital efficiency dimension (theta profit per dollar risked) in opportunity score (0-1). Typical: 0.05 (lowest priority).",
		},
	};

const HEADER_PARAMS = [
	"symbol",
	"ticker",
	"initial_capital",
	"entry_every_n_days",
];

const FILTER_PARAMS = [
	"entry.iv_min_threshold",
	"entry.rsi_min_bull",
	"entry.iv_min_neutral",
	"entry.iv_rv_ratio_min",
	"entry.cooldown_days",
];

const STRATEGY_SECTIONS = [
	{
		title: "Allocazione",
		params: [
			"strategy.initial_allocation",
			"strategy.coherence_factor",
			"strategy.allocation_alpha",
		],
	},
];

const SCORING_SECTIONS = [
	{
		title: "L4 — Entry Score Weights (Trailing)",
		params: [
			"entry_score.w1_iv_rank",
			"entry_score.w2_iv_hv",
			"entry_score.w3_squeeze",
			"entry_score.w4_rsi",
			"entry_score.w5_dte",
			"entry_score.w6_volume",
		],
	},
	{
		title: "L4 — Entry Score Weights (Leading)",
		params: [
			"entry_score.w7_term_structure",
			"entry_score.w8_credit_spread",
			"entry_score.w9_vvix",
		],
	},
	{
		title: "L4 — DTE Range",
		params: [
			"entry_score.dte_min",
			"entry_score.dte_optimal_min",
			"entry_score.dte_optimal_max",
			"entry_score.dte_max",
		],
	},
	{
		title: "L4 — RSI Neutrality",
		params: ["entry_score.rsi_neutral_min", "entry_score.rsi_neutral_max"],
	},
	{
		title: "L5 — Decision",
		params: [
			"decision.threshold_open",
			"decision.threshold_monitor",
			"decision.max_bid_ask_pct",
			"opportunity.weight_edge",
			"opportunity.weight_rr",
			"opportunity.weight_bep",
			"opportunity.weight_execution",
			"opportunity.weight_efficiency",
		],
	},
];

const SIZING_PARAMS = [
	"max_risk",
	"entry_size.threshold_full",
	"entry_size.threshold_reduced",
	"entry_size.multiplier_full",
	"entry_size.multiplier_reduced",
];

const ROLLOUT_PARAMS = ["rollout.enabled", "rollout.min_profit_pct"];

const PORTFOLIO_TRAILING_STOP_PARAMS = [
	"exit.portfolio_trailing_stop.enabled",
	"exit.portfolio_trailing_stop.pullback_pct",
];

// Profit target, stop loss e DTE exit sono ora configurati per-strategia nel tab Strategie.
const EXIT_PARAMS = [
	"exit.rule_trailing_stop.enabled",
	"exit.rule_trailing_stop.min_profit_pct",
	"exit.rule_trailing_stop.pullback_pct",
	"exit.rule_macro_reversal.enabled",
	"exit.rule_momentum_reversal.enabled",
	"exit.rule_momentum_reversal.rsi_threshold",
	"exit.rule_iv_spike.enabled",
	"exit.rule_iv_spike.threshold_ratio",
	"exit.rule_delta_breach.enabled",
	"exit.rule_delta_breach.threshold",
	"exit.rule_theta_decay.enabled",
	"exit.rule_theta_decay.threshold_ratio",
];

const COST_MODEL_PARAMS = [
	"cost_model.commission_per_contract",
	"cost_model.min_commission",
];

const SYSTEM_SECTIONS = [
	{
		title: "Indicatori",
		params: [
			"iv_rank.lookback_days",
			"adx.period",
			"squeeze.bb_percentile",
			"squeeze.macd_threshold",
			"volume.sma_period",
			"alpha_volatility",
			"iv_min",
			"iv_max",
		],
	},
	{
		title: "Debug",
		params: ["debug.force_open"],
	},
];

// ── Per-strategy config ──────────────────────────────────────────────────────

interface StrategyConfig {
	enabled: boolean;
	delta_short: number;
	delta_long: number;
	delta_long_call: number;
	profit_target_pct: number;
	stop_loss_pct: number;
	dte_exit_days: number;
	size_multiplier: number;
}

const STRATEGY_META: Record<string, { label: string; zone: string }> = {
	bull_put_spread:     { label: "Bull Put Spread",      zone: "B" },
	bear_call_spread:    { label: "Bear Call Spread",     zone: "B" },
	iron_condor:         { label: "Iron Condor",          zone: "D" },
	iron_butterfly:      { label: "Iron Butterfly",       zone: "D" },
	bull_call_spread:    { label: "Bull Call Spread",     zone: "A" },
	bear_put_spread:     { label: "Bear Put Spread",      zone: "A" },
	long_straddle:       { label: "Long Straddle",        zone: "C" },
	long_strangle:       { label: "Long Strangle",        zone: "C" },
	put_broken_wing_butterfly: { label: "Put Broken Wing",  zone: "A/C" },
	jade_lizard:         { label: "Jade Lizard",          zone: "B/D" },
	reverse_jade_lizard: { label: "Reverse Jade Lizard",  zone: "B" },
	calendar_spread:     { label: "Calendar Spread",      zone: "D" },
	diagonal_spread:     { label: "Diagonal Spread",      zone: "D" },
};

const ZONE_COLOR: Record<string, string> = {
	A: "blue", B: "orange", C: "green", D: "purple", "A/C": "cyan", "B/D": "gold",
};

const ZONES = ["A", "B", "C", "D"] as const;
type ZoneKey = typeof ZONES[number];

const ZONE_LABELS: Record<ZoneKey, string> = {
	A: "Direzionale / Debit",
	B: "Credit Spread",
	C: "Long Volatilità",
	D: "Neutrale / Range",
};

function _makeZoneCfg(enabledIn: ZoneKey[], base: Omit<StrategyConfig, "enabled">): Record<ZoneKey, StrategyConfig> {
	return Object.fromEntries(
		ZONES.map(z => [z, { ...base, enabled: enabledIn.includes(z) }])
	) as Record<ZoneKey, StrategyConfig>;
}

const DEFAULT_STRATEGY_CONFIG: Record<string, Record<ZoneKey, StrategyConfig>> = {
	bull_put_spread:     _makeZoneCfg(["B"],         { delta_short: 0.20, delta_long: 0.05, delta_long_call: 0.10, profit_target_pct: 50,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	bear_call_spread:    _makeZoneCfg(["B"],         { delta_short: 0.20, delta_long: 0.05, delta_long_call: 0.10, profit_target_pct: 50,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	iron_condor:         _makeZoneCfg(["D"],         { delta_short: 0.10, delta_long: 0.05, delta_long_call: 0.10, profit_target_pct: 40,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	iron_butterfly:      _makeZoneCfg(["D"],         { delta_short: 0.50, delta_long: 0.10, delta_long_call: 0.10, profit_target_pct: 25,  stop_loss_pct: 200, dte_exit_days: 14, size_multiplier: 0.7 }),
	bull_call_spread:    _makeZoneCfg(["A"],         { delta_short: 0.10, delta_long: 0.30, delta_long_call: 0.30, profit_target_pct: 60,  stop_loss_pct: 100, dte_exit_days: 21, size_multiplier: 1.0 }),
	bear_put_spread:     _makeZoneCfg(["A"],         { delta_short: 0.10, delta_long: 0.30, delta_long_call: 0.10, profit_target_pct: 60,  stop_loss_pct: 100, dte_exit_days: 21, size_multiplier: 1.0 }),
	long_straddle:       _makeZoneCfg(["C"],         { delta_short: 0.50, delta_long: 0.00, delta_long_call: 0.00, profit_target_pct: 100, stop_loss_pct: 50,  dte_exit_days: 30, size_multiplier: 0.8 }),
	long_strangle:       _makeZoneCfg(["C"],         { delta_short: 0.30, delta_long: 0.00, delta_long_call: 0.00, profit_target_pct: 100, stop_loss_pct: 50,  dte_exit_days: 30, size_multiplier: 0.8 }),
	put_broken_wing_butterfly: _makeZoneCfg(["A", "C"],   { delta_short: 0.15, delta_long: 0.05, delta_long_call: 0.05, profit_target_pct: 50,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	jade_lizard:         _makeZoneCfg(["B", "D"],   { delta_short: 0.20, delta_long: 0.10, delta_long_call: 0.10, profit_target_pct: 50,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	reverse_jade_lizard: _makeZoneCfg(["B"],         { delta_short: 0.20, delta_long: 0.10, delta_long_call: 0.10, profit_target_pct: 50,  stop_loss_pct: 200, dte_exit_days: 21, size_multiplier: 1.0 }),
	calendar_spread:     _makeZoneCfg(["D"],         { delta_short: 0.40, delta_long: 0.00, delta_long_call: 0.00, profit_target_pct: 50,  stop_loss_pct: 100, dte_exit_days: 7,  size_multiplier: 0.8 }),
	diagonal_spread:     _makeZoneCfg(["D"],         { delta_short: 0.30, delta_long: 0.15, delta_long_call: 0.15, profit_target_pct: 50,  stop_loss_pct: 100, dte_exit_days: 14, size_multiplier: 0.8 }),
};

export default function ParameterEditor({
	currentRun,
	backtestConfig,
	onSave,
	onCancel,
	onEdit,
	loading = false,
	readOnly = false,
}: ParameterEditorProps) {
	const [draft, setDraft] = useState<ParamDraft>(() => {
		const initial: ParamDraft = {};
		if (currentRun?.parameters) {
			for (const [key, param] of Object.entries(currentRun.parameters)) {
				const value =
					typeof param === "string" ? param : (param as ParameterValue).value;
				initial[key] = value;
			}
		}
		return initial;
	});

	const [strategyDraft, setStrategyDraft] = useState<Record<string, Record<string, StrategyConfig>>>(() => {
		const raw = currentRun?.parameters?.["strategy_config.overrides"];
		const jsonStr = typeof raw === "string" ? raw : (raw as any)?.value;
		if (jsonStr) {
			try {
				const parsed = JSON.parse(jsonStr);
				// Detect old flat format (not zone-keyed): first strategy value has top-level "enabled"
				const firstVal = Object.values(parsed)[0] as any;
				if (firstVal && typeof firstVal.enabled !== "undefined") {
					return DEFAULT_STRATEGY_CONFIG;
				}
				return { ...DEFAULT_STRATEGY_CONFIG, ...parsed };
			} catch {}
		}
		return DEFAULT_STRATEGY_CONFIG;
	});

	const updateStrategyField = (
		zone: string,
		strategy: string,
		field: keyof StrategyConfig,
		value: boolean | number,
	) => {
		setStrategyDraft((prev) => ({
			...prev,
			[strategy]: {
				...prev[strategy],
				[zone]: { ...prev[strategy]?.[zone], [field]: value },
			},
		}));
	};

	const paramSchema = useMemo(
		() => (backtestConfig as any)?.parameterSchema || {},
		[backtestConfig]
	);

	const handleSave = () => {
		const params: Record<string, string> = {};

		// Fallback: if paramSchema is empty, extract keys from draft + current run
		const paramKeys =
			Object.keys(paramSchema).length > 0
				? Object.keys(paramSchema)
				: [
						...new Set([
							...Object.keys(draft),
							...(currentRun?.parameters
								? Object.keys(currentRun.parameters)
								: []),
						]),
				  ];

		// Send all parameters, using draft values, currentRun values, or defaults from schema
		for (const key of paramKeys) {
			if (key in draft) {
				params[key] = String(draft[key]);
			} else if (currentRun?.parameters && key in currentRun.parameters) {
				const value = currentRun.parameters[key];
				params[key] = typeof value === "string" ? value : (value as any).value;
			} else if (paramSchema[key]?.default !== undefined) {
				params[key] = String(paramSchema[key].default);
			}
		}

		params["strategy_config.overrides"] = JSON.stringify(strategyDraft);

		onSave(params);
	};

	const PARAM_TYPE_OVERRIDES: Record<string, Partial<ParameterSchema>> = {
		"debug.force_open": { type: "bool", default: "false" },
		"cost_model.commission_per_contract": { type: "float", default: "0.65" },
		"cost_model.min_commission": { type: "float", default: "1.00" },
		"rollout.enabled": { type: "bool", default: "false" },
		"rollout.min_profit_pct": { type: "float", default: "0" },
	};

	const renderField = (paramKey: string) => {
		const schema: ParameterSchema = {
			...(paramSchema[paramKey] ?? {}),
			...(PARAM_TYPE_OVERRIDES[paramKey] ?? {}),
		};
		const hint = PARAMETER_HINTS[paramKey];
		const currentValue = draft[paramKey] ?? schema.default ?? "";
		const precision = (schema as any).precision ?? 2;

		const label = hint ? (
			<span>
				{hint.label}{" "}
				<Tooltip title={hint.description}>
					<QuestionCircleOutlined style={{ color: "#999", marginLeft: 4 }} />
				</Tooltip>
			</span>
		) : (
			paramKey
		);

		// Read-only view mode: render as simple div like INFO panel
		if (readOnly) {
			let displayValue: string | React.ReactNode = String(currentValue);
			if (schema.type === "bool") {
				displayValue =
					String(currentValue).toLowerCase() === "true" ? (
						<span style={{ color: "#22c55e", fontSize: "16px" }}>✓</span>
					) : (
						<span style={{ color: "#ef4444", fontSize: "16px" }}>✕</span>
					);
			} else if (schema.unit && schema.type !== "string") {
				const valueStr = Number(currentValue).toFixed(precision);
				let unitDisplay: React.ReactNode = null;

				if (schema.unit === "pct") {
					unitDisplay = "%";
				} else if (schema.unit !== "value") {
					unitDisplay = (
						<span style={{ color: "#999", marginLeft: 4 }}>{schema.unit}</span>
					);
				}

				displayValue = (
					<>
						{valueStr}
						{unitDisplay}
					</>
				);
			}

			return (
				<div key={paramKey}>
					<div className="text-gray-500 block text-xs font-semibold">
						{label}
					</div>
					<span className="font-medium text-sm">{displayValue}</span>
				</div>
			);
		}

		if (schema.type === "bool") {
			return (
				<Form.Item label={label} key={paramKey} style={{ marginBottom: 4 }}>
					{readOnly ? (
						<span className="font-mono">
							{String(currentValue).toLowerCase() === "true"
								? "✓ Enabled"
								: "✗ Disabled"}
						</span>
					) : (
						<Switch
							checked={String(currentValue).toLowerCase() === "true"}
							onChange={(checked) =>
								setDraft({ ...draft, [paramKey]: String(checked) })
							}
						/>
					)}
				</Form.Item>
			);
		}

		if (paramKey === "strategy.initial_allocation") {
			return (
				<Form.Item label={label} key={paramKey} style={{ marginBottom: 4 }}>
					{readOnly ? (
						<span className="font-mono">{String(currentValue)}</span>
					) : (
						<Select
							value={String(currentValue)}
							onChange={(value) => setDraft({ ...draft, [paramKey]: value })}
							options={[
								{ label: "Neutral", value: "neutral" },
								{ label: "Target", value: "target" },
							]}
						/>
					)}
				</Form.Item>
			);
		}

		if (schema.type === "string") {
			return (
				<Form.Item label={label} key={paramKey} style={{ marginBottom: 2 }}>
					{readOnly ? (
						<span className="font-mono">{String(currentValue)}</span>
					) : (
						<Input
							value={String(currentValue)}
							onChange={(e) =>
								setDraft({ ...draft, [paramKey]: e.target.value })
							}
							placeholder={schema.default}
						/>
					)}
				</Form.Item>
			);
		}

		// Numeric field
		const step = Math.pow(10, -precision);

		return (
			<Form.Item label={label} key={paramKey} style={{ marginBottom: 2 }}>
				{readOnly ? (
					<div className="flex items-center gap-2">
						<span className="font-mono">
							{Number(currentValue).toFixed(precision)}
						</span>
						{schema.unit && (
							<span style={{ color: "#999" }}>{schema.unit}</span>
						)}
					</div>
				) : (
					<InputNumber
						size="small"
						value={Number(currentValue) || undefined}
						onChange={(value) =>
							setDraft({ ...draft, [paramKey]: value ?? "" })
						}
						min={schema.min}
						max={schema.max}
						step={step}
						precision={precision}
						placeholder={schema.default}
						style={{ width: "100%" }}
					/>
				)}
			</Form.Item>
		);
	};

	const ENTRY_FIELDS = [
		{ field: "delta_short"     as const, label: "Δ Short",         min: 0,   max: 1,  step: 0.01, prec: 2 },
		{ field: "delta_long"      as const, label: "Δ Long",          min: 0,   max: 1,  step: 0.01, prec: 2 },
		{ field: "delta_long_call" as const, label: "Δ Long Call",     min: 0,   max: 1,  step: 0.01, prec: 2 },
		{ field: "size_multiplier" as const, label: "Size Multiplier", min: 0.1, max: 2,  step: 0.1,  prec: 1 },
	];

	const EXIT_FIELDS = [
		{ field: "profit_target_pct" as const, label: "Profit Target %", min: 0, max: 500,  step: 5,  prec: 0 },
		{ field: "stop_loss_pct"     as const, label: "Stop Loss %",     min: 0, max: 1000, step: 10, prec: 0 },
		{ field: "dte_exit_days"     as const, label: "DTE Exit (days)", min: 1, max: 90,   step: 1,  prec: 0 },
	];

	const renderStrategyFields = (zone: string, key: string, cfg: StrategyConfig, fields: typeof ENTRY_FIELDS | typeof EXIT_FIELDS) =>
		fields.map(({ field, label, min, max, step, prec }) => (
			<Form.Item key={field} label={label} style={{ marginBottom: 4 }}>
				<InputNumber
					size="small"
					value={cfg[field] as number}
					onChange={(v) => updateStrategyField(zone, key, field, v ?? 0)}
					min={min}
					max={max}
					step={step}
					precision={prec}
					disabled={!cfg.enabled}
					style={{ width: "100%" }}
				/>
			</Form.Item>
		));

	const renderStrategiesForZone = (zone: ZoneKey) => {
		const items = Object.entries(STRATEGY_META).map(([key, meta]) => {
			const cfg = strategyDraft[key]?.[zone] ?? DEFAULT_STRATEGY_CONFIG[key]?.[zone];
			if (!cfg) return null;
			return {
				key,
				label: (() => {
					const sm = getStrategyMeta(key);
					return (
						<div className="flex items-center gap-2 w-full pr-2">
							<Switch
								size="small"
								checked={cfg.enabled}
								onChange={(v) => updateStrategyField(zone, key, "enabled", v)}
							/>
							<span className={cfg.enabled ? "font-medium" : "text-gray-400"}>
								{meta.label}
							</span>
							{sm && (
								<Tag color={sm.color} style={{ fontSize: 10 }}>
									{sm.acronym}
								</Tag>
							)}
						</div>
					);
				})(),
				children: (
					<div>
						<div className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-2">Entry</div>
						<div className="grid grid-cols-2 gap-x-4 gap-y-1">
							{renderStrategyFields(zone, key, cfg, ENTRY_FIELDS)}
						</div>
						<Divider style={{ margin: "10px 0" }} />
						<div className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-2">Exit</div>
						<div className="grid grid-cols-2 gap-x-4 gap-y-1">
							{renderStrategyFields(zone, key, cfg, EXIT_FIELDS)}
						</div>
					</div>
				),
			};
		}).filter(Boolean);

		return (
			<Collapse size="small" collapsible="icon" items={items as any} ghost />
		);
	};

	const renderStrategyAccordion = () => {
		const tabItems = ZONES.map(zone => ({
			key: zone,
			label: (
				<span className="flex items-center gap-1">
					<Tag color={ZONE_COLOR[zone]} style={{ margin: 0, fontSize: 11 }}>{zone}</Tag>
					<span className="text-xs text-gray-500 hidden sm:inline">{ZONE_LABELS[zone]}</span>
				</span>
			),
			children: (
				<div style={{ paddingTop: 4 }}>
					{renderStrategiesForZone(zone)}
				</div>
			),
		}));

		return (
			<div style={{ paddingTop: 8 }}>
				<Tabs size="small" items={tabItems} />
				<div className="flex justify-end mt-2">
					<Button
						size="small"
						type="primary"
						icon={<CheckOutlined />}
						onClick={handleSave}
						loading={loading}
					>
						Salva strategie
					</Button>
				</div>
			</div>
		);
	};

	const renderSections = (
		sections: Array<{ title: string; params: string[] }>
	) => (
		<div style={{ paddingTop: 12 }}>
			{sections.map(({ title, params }, i) => (
				<div key={title}>
					<Divider
						orientation="left"
						orientationMargin={0}
						style={{
							fontSize: 12,
							color: "#888",
							marginTop: i === 0 ? 4 : 16,
							marginBottom: 8,
						}}
					>
						{title}
					</Divider>
					<div className="grid grid-cols-2 gap-2">
						{params.map(renderField)}
					</div>
				</div>
			))}
		</div>
	);

	return (
		<Card
			size="small"
			title={
				<div style={{ display: "flex", alignItems: "center", gap: 8 }}>
					<SettingOutlined />
					<span>EXECUTION PARAMETERS</span>
				</div>
			}
			extra={
				<div style={{ display: "flex", gap: 8 }}>
					{readOnly && onEdit ? (
						<Button type="primary" icon={<EditOutlined />} onClick={onEdit}>
							Edit
						</Button>
					) : (
						<>
							<Button icon={<CloseOutlined />} onClick={onCancel}>
								Cancel
							</Button>
							<Button
								type="primary"
								icon={<CheckOutlined />}
								onClick={handleSave}
								loading={loading}
							>
								Save
							</Button>
						</>
					)}
				</div>
			}
		>
			<Form layout="vertical" style={{ maxWidth: 600 }}>
				{/* Header Section */}
				{HEADER_PARAMS.length > 0 && (
					<>
						<div className="grid grid-cols-2 gap-2">
							{HEADER_PARAMS.map(renderField)}
						</div>
						<Divider />
					</>
				)}

				{/* Tabs for Entry, Strategy, Exit */}
				<Tabs
					tabBarExtraContent={
						<Tooltip title="Parameters are validated server-side. Invalid values will be rejected with detailed error messages.">
							<InfoCircleOutlined
								style={{ color: "#666", cursor: "pointer", fontSize: "16px" }}
							/>
						</Tooltip>
					}
					items={[
						{
							key: "filtri",
							label: "Filtri",
							children: (
								<div
									className="grid grid-cols-2 gap-2"
									style={{ paddingTop: 12 }}
								>
									{FILTER_PARAMS.map(renderField)}
								</div>
							),
						},
						{
							key: "strategia",
							label: "Strategie",
							children: (
								<>
									{renderSections(STRATEGY_SECTIONS)}
									<Divider
										orientation="left"
										orientationMargin={0}
										style={{ fontSize: 12, color: "#888", marginTop: 16, marginBottom: 0 }}
									>
										Configurazione per Strategia
									</Divider>
									{renderStrategyAccordion()}
								</>
							),
						},
						{
							key: "scoring",
							label: "Scoring",
							children: renderSections(SCORING_SECTIONS),
						},
						{
							key: "sizing",
							label: "Sizing",
							children: (
								<div style={{ paddingTop: 12 }}>
									<div className="grid grid-cols-2 gap-2">
										{SIZING_PARAMS.map(renderField)}
									</div>
									<Divider
										orientation="left"
										orientationMargin={0}
										style={{ fontSize: 12, color: "#888", marginTop: 16, marginBottom: 8 }}
									>
										Commissioni (IBKR)
									</Divider>
									<div className="grid grid-cols-2 gap-2">
										{COST_MODEL_PARAMS.map(renderField)}
									</div>
								</div>
							),
						},
						{
							key: "exit",
							label: "Exit",
							children: (
								<div style={{ paddingTop: 12 }}>
									<div className="grid grid-cols-2 gap-2">
										{EXIT_PARAMS.map(renderField)}
									</div>
									<Divider
										orientation="left"
										orientationMargin={0}
										style={{ fontSize: 12, color: "#888", marginTop: 16, marginBottom: 8 }}
									>
										Rollout
									</Divider>
									<div className="grid grid-cols-2 gap-2">
										{ROLLOUT_PARAMS.map(renderField)}
									</div>
									<Divider
										orientation="left"
										orientationMargin={0}
										style={{ fontSize: 12, color: "#888", marginTop: 16, marginBottom: 8 }}
									>
										Portfolio Trailing Stop
									</Divider>
									<div className="grid grid-cols-2 gap-2">
										{PORTFOLIO_TRAILING_STOP_PARAMS.map(renderField)}
									</div>
								</div>
							),
						},
						{
							key: "system",
							label: "System",
							children: (
								<div style={{ paddingTop: 12 }}>
									{renderSections([SYSTEM_SECTIONS[0]])}
									<Divider
										orientation="left"
										orientationMargin={0}
										style={{
											fontSize: 12,
											color: "#888",
											marginTop: 16,
											marginBottom: 8,
										}}
									>
										Debug
									</Divider>
									<div className="text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded p-2 mb-3">
										Force Open è attivo per default: il threshold L5 è temporaneamente disabilitato perché l'opportunity score ha un bias strutturale contro le credit strategies. Verrà ricalibrато nel Sprint 3.
									</div>
									<div className="grid grid-cols-2 gap-2">
										{SYSTEM_SECTIONS[1].params.map(renderField)}
									</div>
								</div>
							),
						},
					]}
				/>
			</Form>
		</Card>
	);
}
