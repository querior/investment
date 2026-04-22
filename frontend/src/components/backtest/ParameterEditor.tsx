import { useState, useMemo } from "react";
import {
	Button,
	Card,
	Divider,
	Form,
	Input,
	InputNumber,
	Select,
	Switch,
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
		"max_risk": {
			label: "Max Risk",
			description: "Maximum allowed risk per trade (percentage).",
		},

		// Entry - Strike Delta
		"entry.target_delta_short": {
			label: "Target Delta (Short)",
			description:
				"Target delta for short call/put strikes (0-1). Higher = closer to ATM, lower = further OTM.",
		},
		"entry.target_delta_long": {
			label: "Target Delta (Long)",
			description:
				"Target delta for long protective calls/puts (0-1). Higher = closer to ATM, lower = further OTM.",
		},
		"entry.cooldown_days": {
			label: "Cooldown After Close (days)",
			description:
				"Minimum days before reopening the same strategy after it closes. Prevents rapid open/close cycles.",
		},

		// Entry Scoring - Weights
		"entry_score.w1_iv_rank": {
			label: "Weight: IV Rank",
			description: "Weight for IV Rank component in entry score (0-1). Normalized with other weights.",
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
			description: "Weight for Days to Expiration component in entry score (0-1).",
		},
		"entry_score.w6_volume": {
			label: "Weight: Volume Ratio",
			description: "Weight for volume ratio component in entry score (0-1).",
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
		"alpha_volatility": {
			label: "Alpha Volatility",
			description:
				"Scaling factor for volatility-based position sizing. Higher = more size in high vol.",
		},
		"iv_min": {
			label: "IV Minimum",
			description:
				"Absolute minimum IV threshold for any entry (0-1). Filters out ultra-low premium.",
		},
		"iv_max": {
			label: "IV Maximum",
			description:
				"Absolute maximum IV threshold for any entry (0-2). Filters out excessive premium.",
		},

		// Execution
		"entry_every_n_days": {
			label: "Entry Every N Days",
			description:
				"Frequency of entry signals (days). 30 = check for new entries every 30 days.",
		},
		"ticker": {
			label: "Ticker",
			description: "Underlying ticker symbol (IWM, SPY, QQQ, etc.).",
		},
	};

const ENTRY_PARAMS = [
	// Basic entry filters
	"entry.iv_min_threshold",
	"entry.rsi_min_bull",
	"entry.iv_min_neutral",
	"entry.iv_rv_ratio_min",
	"entry.target_delta_short",
	"entry.target_delta_long",
	"entry.cooldown_days",
	"max_risk",
	// Entry scoring weights
	"entry_score.w1_iv_rank",
	"entry_score.w2_iv_hv",
	"entry_score.w3_squeeze",
	"entry_score.w4_rsi",
	"entry_score.w5_dte",
	"entry_score.w6_volume",
	// Position sizing
	"entry_size.threshold_full",
	"entry_size.threshold_reduced",
];

const STRATEGY_PARAMS = [
	"strategy.initial_allocation",
	"strategy.coherence_factor",
	"strategy.allocation_alpha",
];

const EXIT_PARAMS = [
	"exit.rule_dte.enabled",
	"exit.rule_dte.threshold_days",
	"exit.rule_profit_target.enabled",
	"exit.rule_profit_target.threshold_pct",
	"exit.rule_stop_loss.enabled",
	"exit.rule_stop_loss.threshold_pct",
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

const PIPELINE_PARAMS = [
	"iv_rank.lookback_days",
	"adx.period",
	"squeeze.bb_percentile",
	"squeeze.macd_threshold",
	"volume.sma_period",
	"alpha_volatility",
	"iv_min",
	"iv_max",
];

const HEADER_PARAMS = ["symbol", "ticker", "initial_capital", "entry_every_n_days"];

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

	const paramSchema = useMemo(
		() => (backtestConfig as any)?.parameterSchema || {},
		[backtestConfig]
	);

	const handleSave = () => {
		const params: Record<string, string> = {};

		// Fallback: if paramSchema is empty, extract keys from draft + current run
		const paramKeys = Object.keys(paramSchema).length > 0
			? Object.keys(paramSchema)
			: [...new Set([
				...Object.keys(draft),
				...(currentRun?.parameters ? Object.keys(currentRun.parameters) : [])
			])];

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

		onSave(params);
	};

	const renderField = (paramKey: string) => {
		const schema: ParameterSchema = paramSchema[paramKey] || {};
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
							<InfoCircleOutlined style={{ color: "#666", cursor: "pointer", fontSize: "16px" }} />
						</Tooltip>
					}
					items={[
						{
							key: "entry",
							label: "Entry",
							children: (
								<div
									className="grid grid-cols-2 gap-2"
									style={{ paddingTop: 12 }}
								>
									{ENTRY_PARAMS.map(renderField)}
								</div>
							),
						},
						{
							key: "strategy",
							label: "Strategy",
							children: (
								<div
									className="grid grid-cols-2 gap-2"
									style={{ paddingTop: 12 }}
								>
									{STRATEGY_PARAMS.map(renderField)}
								</div>
							),
						},
						{
							key: "exit",
							label: "Exit",
							children: (
								<div
									className="grid grid-cols-2 gap-2"
									style={{ paddingTop: 12 }}
								>
									{EXIT_PARAMS.map(renderField)}
								</div>
							),
						},
						{
							key: "pipeline",
							label: "Pipeline",
							children: (
								<div
									className="grid grid-cols-2 gap-2"
									style={{ paddingTop: 12 }}
								>
									{PIPELINE_PARAMS.map(renderField)}
								</div>
							),
						},
					]}
				/>
			</Form>
		</Card>
	);
}
