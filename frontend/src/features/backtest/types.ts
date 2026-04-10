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
	cagr: number | null;
	sharpe: number | null;
	volatility: number | null;
	max_drawdown: number | null;
	win_rate: number | null;
	profit_factor: number | null;
	n_trades: number | null;
	created_at: string;
	updated_at: string;
	parameters: Record<string, RunParameter>;
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

export type BacktestState = {
	// list
	backtests: BacktestDto[];
	total: number;
	page: number;
	loading: boolean;
	error: string | null;
	// create backtest
	creating: boolean;
	createError: string | null;
	lastCreatedId: number | null;
	// current backtest detail
	current: BacktestDto | null;
	currentLoading: boolean;
	// runs for current backtest
	runs: BacktestRunDto[];
	runsLoading: boolean;
	// create/execute run
	creatingRun: boolean;
	executingRunId: number | null;
	invalidatingRunId: number | null;
	// run detail
	currentRun: BacktestRunDto | null;
	currentRunLoading: boolean;
	runWeights: RunWeightDto[];
	runWeightsLoading: boolean;
	portfolioPerformances: PortfolioPerformanceState;
	positions: PositionsState;
	// backtest config
	backtestConfig: BacktestConfigDto | null;
	backtestConfigLoading: boolean;
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
