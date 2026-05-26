export type BacktestStatus = "READY" | "RUNNING" | "DONE" | "ERROR" | "STOPPED";

export enum FrequencyType {
	EOM = "EOM",
	EOD = "EOD",
	EOW = "EOW",
}

export type BacktestDto = {
	id: number;
	name: string;
	description: string | null;
	strategy_version: string;
	frequency: FrequencyType;
	instrument?: string;
	created_at: string;
	updated_at: string;
};

export type InitialAllocation = "target" | "neutral";
export type Instrument = "options" | "futures";

export type RunParameter = {
	value: string;
	unit: string;
};

export type MetricsSummary = {
	cagr: number | null;
	sharpe: number | null;
	volatility: number | null;
	max_drawdown: number | null;
	win_rate: number | null;
	profit_factor: number | null;
	max_consecutive_losses: number | null;
	n_trades: number | null;
};

export type ZonePerformance = {
	count: number;
	winning: number;
	losing: number;
	win_rate: number;
	total_pnl: number;
	avg_pnl: number;
	avg_holding_days: number;
};

export type StrategyPerformance = {
	strategy: string;
	strategy_acronym: string | null;
	strategy_name: string | null;
	strategy_color: string;
	count: number;
	winning: number;
	losing: number;
	win_rate: number;
	avg_holding_days: number;
	total_pnl: number;
	avg_pnl: number;
	max_drawdown: number | null;
	zone_breakdown?: Record<string, ZonePerformance>;
};

export type BacktestRunDto = {
	id: number;
	backtest_id: number;
	name: string | null;
	start_date: string;
	end_date: string;
	frequency: string;
	config_snapshot: string | null; // JSON
	status: BacktestStatus;
	notes: string | null;
	error_message: string | null;
	created_at: string;
	updated_at: string;
	parameters: Record<string, RunParameter>;
	// Fields from metrics endpoint
	summary?: MetricsSummary;
	entry_rules?: Record<string, string>;
	exit_rules?: Record<string, string>;
	performances?: StrategyPerformance[];
	nav?: NavDataPoint[];
	portfolio_timeseries?: PortfolioTimeseriesPoint[];
};

export type BacktestListResponse = {
	items: BacktestDto[];
	total: number;
	page: number;
	limit: number;
};

export type CreateBacktestPayload = {
	name: string;
	description?: string;
	strategy_version?: string;
	frequency?: string;
	instrument?: Instrument;
};

export type CreateRunPayload = {
	name?: string;
	start: string;
	end: string;
	notes?: string;
	initial_allocation?: InitialAllocation;
};

export type AdjustmentDto = {
	pillar: string;
	regime: string;
	asset: string;
	delta: number;
};

export type BacktestConfigDto = {
	neutral: Record<string, number>;
	coherence_factor: number;
	allocation_alpha: number;
	adjustments: AdjustmentDto[];
};

// Alias used in BacktestRunDetail
export type AllocationConfig = BacktestConfigDto;

export type RunWeightDto = {
	date: string;
	asset: string;
	weight: number;
	pillar_scores: string | null; // JSON string: {"Growth": "expansion", ...}
};

export type BacktestPortfolioPerformanceDto = {
	snapshot_date: string;
	cash: number;
	positions_value: number;
	total_equity: number;
	realized_pnl: number;
	unrealized_pnl: number;
	total_pnl: number;
	total_delta: number;
	total_gamma: number;
	total_theta: number;
	total_vega: number;
	open_positions_count: number;
	closed_positions_count: number;
	new_positions_count: number;
	underlying_price: number;
	iv: number;
};

export type BacktestPositionDto = {
	id: number;
	position_type: string;
	strategy_name: string | null;
	strategy_acronym: string | null;
	strategy_color: string;
	status: string;
	opened_at: string;
	closed_at: string | null;
	entry_underlying: number;
	entry_iv: number;
	entry_macro_regime: string | null;
	initial_value: number;
	close_value: number | null;
	realized_pnl: number | null;
	unrealized_pnl: number | null;
	performance_pct: number | null;
	days_in_trade: number;
	entry_max_loss: number | null;
	entry_max_profit: number | null;
	entry_prob_profit: number | null;
	entry_ev_net: number | null;
	capital_at_risk_pct: number | null;
	risk_limit_ok: boolean | null;
};

export type BacktestPositionHistoryDto = {
	snapshot_date: string;
	underlying_price: number;
	iv: number;
	position_price: number;
	position_pnl: number;
	position_delta: number;
	position_gamma: number;
	position_theta: number;
	position_vega: number;
	min_dte: number;
	is_open: boolean;
};

export type PortfolioPerformanceState = {
	items: BacktestPortfolioPerformanceDto[];
	page: number;
	page_size: number;
	total: number;
};

export type PositionsState = {
	items: BacktestPositionDto[];
	page: number;
	page_size: number;
	total: number;
};

export type NavDataPoint = {
	date: string;
	nav: number;
	period_return: number;
};

export type PortfolioTimeseriesPoint = {
	snapshot_date: string;
	total_equity: number;
	realized_pnl: number;
	unrealized_pnl: number;
	total_pnl: number;
	underlying_price: number;
	iv: number;
};

export type BacktestState = {
	// list
	backtests: BacktestDto[];
	total: number;
	page: number;
	loading: boolean;
	error: string | null;
	lastCreatedId: number | null;
	// current backtest detail
	current: BacktestDto | null;
	// runs for current backtest
	runs: BacktestRunDto[];
	executingRunId: number | null;
	invalidatingRunId: number | null;
	// run detail
	currentRun: BacktestRunDto | null;
	runWeights: RunWeightDto[];
	portfolioPerformances: PortfolioPerformanceState;
	positionLoading: boolean;
	positions: PositionsState;
	// nav data for chart
	navData: NavDataPoint[];
	// backtest config
	backtestConfig: BacktestConfigDto | null;
	// decision logs
	decisionLogs: DecisionLogsState;
	// decision matrix
	decisionMatrix: DecisionMatrixState;
};

export const STATUS_BADGE: Record<
	BacktestStatus,
	{
		status: "default" | "processing" | "error" | "success" | "warning";
		text: string;
	}
> = {
	READY: { status: "default", text: "Ready" },
	RUNNING: { status: "processing", text: "Running" },
	DONE: { status: "success", text: "Done" },
	ERROR: { status: "error", text: "Error" },
	STOPPED: { status: "warning", text: "Stopped" },
};

export const INITIAL_ALLOCATION_OPTIONS: {
	value: InitialAllocation;
	label: string;
}[] = [
	{ value: "neutral", label: "Neutral weights" },
	{ value: "target", label: "First target" },
];

export const INSTRUMENT_OPTIONS: {
	value: Instrument;
	label: string;
}[] = [
	{ value: "options", label: "Options" },
	{ value: "futures", label: "Futures" },
];

// Decision Logs
export type DecisionLog = {
	id: number;
	date: string;
	zone: string | null;
	trend: string | null;
	iv_rank: number | null;
	adx: number | null;
	entry_score: number | null;
	strategy_name: string;
	size_multiplier: number;
	should_trade: boolean;
	spot: number | null;
	iv: number | null;
	dte_days: number | null;
	delta: number | null;
	gamma: number | null;
	vega: number | null;
	theta: number | null;
	bid_ask_spread: number | null;
	bid_ask_pct: number | null;
	edge: number | null;
	breakeven_distance: number | null;
	decision_action: string;
	decision_score: number;
	decision_reasoning: string | null;
	pricing_edge_score: number | null;
	risk_reward_score: number | null;
	breakeven_score: number | null;
	execution_cost_score: number | null;
	capital_efficiency_score: number | null;
	iv_term_slope_delta5: number | null;
	credit_spread_delta5: number | null;
	vvix_rank: number | null;
};

export type DecisionMatrixRow = {
	zone: string | null;
	strategy_name: string;
	decision_action: string;
	count: number;
	avg_score: number | null;
	avg_entry_score: number | null;
	avg_iv_rank: number | null;
	avg_adx: number | null;
	avg_pricing_edge: number | null;
	avg_risk_reward: number | null;
	avg_breakeven: number | null;
	avg_execution_cost: number | null;
	avg_capital_efficiency: number | null;
};

export type ZoneStat = {
	n_closed: number;
	win_rate: number;
	avg_pnl: number;
	max_drawdown: number;
};

export type DecisionMatrixState = {
	rows: DecisionMatrixRow[];
	zone_stats: Record<string, ZoneStat>;
	loading: boolean;
	error: string | null;
};

export type DecisionLogsState = {
	items: DecisionLog[];
	page: number;
	page_size: number;
	total: number;
	loading: boolean;
	error: string | null;
	filters?: {
		decision_actions?: string[];
		strategy_names?: string[];
		date_from?: string;
		date_to?: string;
		min_entry_score?: number;
		max_entry_score?: number;
		min_size_multiplier?: number;
		max_size_multiplier?: number;
	};
};
