import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type {
	BacktestConfigDto,
	BacktestDto,
	BacktestPositionDto,
	BacktestRunDto,
	BacktestState,
	CreateBacktestPayload,
	CreateRunPayload,
	RunParameter,
	RunWeightDto,
} from "./types";

const initialState: BacktestState = {
	backtests: [],
	total: 0,
	page: 1,
	loading: false,
	error: null,
	lastCreatedId: null,
	current: null,
	runs: [],
	executingRunId: null,
	invalidatingRunId: null,
	currentRun: null,
	runWeights: [],
	portfolioPerformances: {
		items: [],
		page: 1,
		page_size: 20,
		total: 0,
	},
	positionLoading: false,
	positions: {
		items: [],
		page: 1,
		page_size: 20,
		total: 0,
	},
	backtestConfig: null,
};

const slice = createSlice({
	name: "backtest",
	initialState,
	reducers: {
		// --- list ---
		fetchBacktestsRequest(
			state,
			_action: PayloadAction<{ page?: number; limit?: number } | undefined>
		) {
			state.loading = true;
			state.error = null;
		},
		fetchBacktestsSuccess(
			state,
			action: PayloadAction<{
				items: BacktestDto[];
				total: number;
				page: number;
			}>
		) {
			state.loading = false;
			state.backtests = action.payload.items;
			state.total = action.payload.total;
			state.page = action.payload.page;
		},
		// --- detail ---
		fetchBacktestRequest(state, _action: PayloadAction<number>) {
			state.loading = true;
			state.current = null;
		},
		fetchBacktestSuccess(state, action: PayloadAction<BacktestDto>) {
			state.loading = false;
			state.current = action.payload;
		},
		// --- create backtest ---
		createBacktestRequest(
			state,
			_action: PayloadAction<CreateBacktestPayload>
		) {
			state.loading = true;
			state.error = null;
			state.lastCreatedId = null;
		},
		createBacktestSuccess(state, action: PayloadAction<number>) {
			state.loading = false;
			state.lastCreatedId = action.payload;
		},
		clearLastCreatedId(state) {
			state.lastCreatedId = null;
		},
		// --- update backtest ---
		updateBacktestRequest(
			_state,
			_action: PayloadAction<{
				id: number;
				name?: string;
				description?: string;
			}>
		) {},
		updateBacktestSuccess(state, action: PayloadAction<number>) {
			if (state.current?.id === action.payload) state.current = null;
		},
		// --- delete backtest ---
		deleteBacktestRequest(_state, _action: PayloadAction<number>) {},
		deleteBacktestSuccess(state, action: PayloadAction<number>) {
			state.backtests = state.backtests.filter((b) => b.id !== action.payload);
		},
		// --- runs ---
		fetchRunsRequest(state, _action: PayloadAction<number>) {
			state.loading = true;
			state.runs = [];
		},
		fetchRunsSuccess(state, action: PayloadAction<BacktestRunDto[]>) {
			state.loading = false;
			state.runs = action.payload;
		},
		// --- create run ---
		createRunRequest(
			state,
			_action: PayloadAction<{ backtestId: number; payload: CreateRunPayload }>
		) {
			state.loading = true;
		},
		createRunSuccess(state, action: PayloadAction<BacktestRunDto>) {
			state.loading = false;
			state.runs = [action.payload, ...state.runs];
		},
		cloneRunRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.loading = true;
		},
		// --- update run ---
		updateRunRequest(
			_state,
			_action: PayloadAction<{
				backtestId: number;
				runId: number;
				patch: {
					name?: string;
					start?: string;
					end?: string;
					parameters?: Record<string, string>;
				};
			}>
		) {},
		updateRunSuccess(
			state,
			action: PayloadAction<{
				runId: number;
				patch: {
					name?: string;
					start?: string;
					end?: string;
					parameters?: Record<string, string>;
				};
			}>
		) {
			const { name, start, end, parameters } = action.payload.patch;
			const applyTo = (run: BacktestRunDto) => {
				if (name !== undefined) run.name = name;
				if (start !== undefined) run.start_date = start;
				if (end !== undefined) run.end_date = end;
				if (parameters !== undefined)
					run.parameters = {
						...run.parameters,
						...(parameters as unknown as Record<string, RunParameter>),
					};
			};
			const run = state.runs.find((r) => r.id === action.payload.runId);
			if (run) applyTo(run);
			if (state.currentRun?.id === action.payload.runId)
				applyTo(state.currentRun);
		},
		// --- delete run ---
		deleteRunRequest(
			_state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {},
		deleteRunSuccess(state, action: PayloadAction<number>) {
			state.runs = state.runs.filter((r) => r.id !== action.payload);
		},
		// --- run detail ---
		fetchRunDetailRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.positionLoading = true;
			state.currentRun = null;
		},
		fetchRunDetailSuccess(state, action: PayloadAction<BacktestRunDto>) {
			state.positionLoading = false;
			state.currentRun = action.payload;
		},
		// --- run weights ---
		fetchRunWeightsRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.loading = true;
			state.runWeights = [];
		},
		fetchRunWeightsSuccess(state, action: PayloadAction<RunWeightDto[]>) {
			state.loading = false;
			state.runWeights = action.payload;
		},
		// --- portfolio performance ---
		fetchPortfolioPerformanceRequest(
			state,
			_action: PayloadAction<{
				backtestId: number;
				runId: number;
				page?: number;
				limit?: number;
			}>
		) {
			state.loading = true;
		},
		fetchPortfolioPerformanceSuccess(
			state,
			action: PayloadAction<{
				items: BacktestPositionDto[];
				total: number;
				page: number;
				limit: number;
			}>
		) {
			state.loading = false;
			state.positions = {
				items: action.payload.items,
				page: action.payload.page,
				page_size: action.payload.limit,
				total: action.payload.total,
			};
		},
		// --- backtest config ---
		fetchBacktestConfigRequest(state, _action: PayloadAction<number>) {
			state.loading = true;
		},
		fetchBacktestConfigSuccess(
			state,
			action: PayloadAction<BacktestConfigDto>
		) {
			state.loading = false;
			state.backtestConfig = action.payload;
		},
		// --- execute run ---
		executeRunRequest(
			state,
			action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.executingRunId = action.payload.runId;
			const run = state.runs.find((r) => r.id === action.payload.runId);
			if (run) run.status = "RUNNING";
			if (state.currentRun?.id === action.payload.runId)
				state.currentRun.status = "RUNNING";
		},
		executeRunSuccess(state, action: PayloadAction<number>) {
			state.executingRunId = null;
		},
		// --- stop run ---
		stopRunRequest(
			state,
			action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			// polling aggiornerà lo status; mostriamo solo loading sul bottone
		},
		stopRunSuccess(_state, _action: PayloadAction<void>) {},
		// --- invalidate run ---
		invalidateRunRequest(
			state,
			action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.invalidatingRunId = action.payload.runId;
		},
		invalidateRunSuccess(state, action: PayloadAction<number>) {
			state.invalidatingRunId = null;
			const reset = (run: BacktestRunDto) => {
				run.status = "READY";
				run.cagr = null;
				run.sharpe = null;
				run.volatility = null;
				run.max_drawdown = null;
				run.win_rate = null;
				run.profit_factor = null;
				run.n_trades = null;
			};
			const run = state.runs.find((r) => r.id === action.payload);
			if (run) reset(run);
			if (state.currentRun?.id === action.payload) {
				reset(state.currentRun);
				state.runWeights = [];
			}
		},
		backtestActionFailure(state, action: PayloadAction<string>) {
			state.loading = false;
			state.error = action.payload;
		},
	},
});

export const {
	fetchBacktestsRequest,
	fetchBacktestsSuccess,
	fetchBacktestRequest,
	fetchBacktestSuccess,
	createBacktestRequest,
	createBacktestSuccess,
	clearLastCreatedId,
	updateBacktestRequest,
	updateBacktestSuccess,
	deleteBacktestRequest,
	deleteBacktestSuccess,
	fetchRunsRequest,
	fetchRunsSuccess,
	createRunRequest,
	createRunSuccess,
	cloneRunRequest,
	updateRunRequest,
	updateRunSuccess,
	deleteRunRequest,
	deleteRunSuccess,
	executeRunRequest,
	executeRunSuccess,
	stopRunRequest,
	stopRunSuccess,
	invalidateRunRequest,
	invalidateRunSuccess,
	fetchRunDetailRequest,
	fetchRunDetailSuccess,
	fetchRunWeightsRequest,
	fetchRunWeightsSuccess,
	fetchPortfolioPerformanceRequest,
	fetchPortfolioPerformanceSuccess,
	fetchBacktestConfigRequest,
	fetchBacktestConfigSuccess,
	backtestActionFailure,
} = slice.actions;

export default slice.reducer;
