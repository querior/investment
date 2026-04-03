import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type {
	BacktestConfigDto,
	BacktestDto,
	BacktestRunDto,
	BacktestState,
	CreateBacktestPayload,
	CreateRunPayload,
	RunWeightDto,
} from "./types";

const initialState: BacktestState = {
	backtests: [],
	total: 0,
	page: 1,
	loading: false,
	error: null,
	creating: false,
	createError: null,
	lastCreatedId: null,
	current: null,
	currentLoading: false,
	runs: [],
	runsLoading: false,
	creatingRun: false,
	executingRunId: null,
	invalidatingRunId: null,
	currentRun: null,
	currentRunLoading: false,
	runWeights: [],
	runWeightsLoading: false,
	backtestConfig: null,
	backtestConfigLoading: false,
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
		fetchBacktestsFailure(state, action: PayloadAction<string>) {
			state.loading = false;
			state.error = action.payload;
		},
		// --- detail ---
		fetchBacktestRequest(state, _action: PayloadAction<number>) {
			state.currentLoading = true;
			state.current = null;
		},
		fetchBacktestSuccess(state, action: PayloadAction<BacktestDto>) {
			state.currentLoading = false;
			state.current = action.payload;
		},
		fetchBacktestFailure(state, action: PayloadAction<string>) {
			state.currentLoading = false;
			state.error = action.payload;
		},
		// --- create backtest ---
		createBacktestRequest(
			state,
			_action: PayloadAction<CreateBacktestPayload>
		) {
			state.creating = true;
			state.createError = null;
			state.lastCreatedId = null;
		},
		createBacktestSuccess(state, action: PayloadAction<number>) {
			state.creating = false;
			state.lastCreatedId = action.payload;
		},
		createBacktestFailure(state, action: PayloadAction<string>) {
			state.creating = false;
			state.createError = action.payload;
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
		updateBacktestFailure(_state, _action: PayloadAction<number>) {},
		// --- delete backtest ---
		deleteBacktestRequest(_state, _action: PayloadAction<number>) {},
		deleteBacktestSuccess(state, action: PayloadAction<number>) {
			state.backtests = state.backtests.filter((b) => b.id !== action.payload);
		},
		deleteBacktestFailure(_state, _action: PayloadAction<number>) {},
		// --- runs ---
		fetchRunsRequest(state, _action: PayloadAction<number>) {
			state.runsLoading = true;
			state.runs = [];
		},
		fetchRunsSuccess(state, action: PayloadAction<BacktestRunDto[]>) {
			state.runsLoading = false;
			state.runs = action.payload;
		},
		fetchRunsFailure(state, action: PayloadAction<string>) {
			state.runsLoading = false;
			state.error = action.payload;
		},
		// --- create run ---
		createRunRequest(
			state,
			_action: PayloadAction<{ backtestId: number; payload: CreateRunPayload }>
		) {
			state.creatingRun = true;
		},
		createRunSuccess(state, action: PayloadAction<BacktestRunDto>) {
			state.creatingRun = false;
			state.runs = [action.payload, ...state.runs];
		},
		cloneRunRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.creatingRun = true;
		},
		createRunFailure(state, action: PayloadAction<string>) {
			state.creatingRun = false;
			state.error = action.payload;
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
					run.parameters = { ...run.parameters, ...parameters };
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
		deleteRunFailure(_state, _action: PayloadAction<number>) {},
		// --- run detail ---
		fetchRunDetailRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.currentRunLoading = true;
			state.currentRun = null;
		},
		fetchRunDetailSuccess(state, action: PayloadAction<BacktestRunDto>) {
			state.currentRunLoading = false;
			state.currentRun = action.payload;
		},
		fetchRunDetailFailure(state, action: PayloadAction<string>) {
			state.currentRunLoading = false;
			state.error = action.payload;
		},
		// --- run weights ---
		fetchRunWeightsRequest(
			state,
			_action: PayloadAction<{ backtestId: number; runId: number }>
		) {
			state.runWeightsLoading = true;
			state.runWeights = [];
		},
		fetchRunWeightsSuccess(state, action: PayloadAction<RunWeightDto[]>) {
			state.runWeightsLoading = false;
			state.runWeights = action.payload;
		},
		fetchRunWeightsFailure(state, action: PayloadAction<string>) {
			state.runWeightsLoading = false;
		},
		// --- backtest config ---
		fetchBacktestConfigRequest(state, _action: PayloadAction<number>) {
			state.backtestConfigLoading = true;
		},
		fetchBacktestConfigSuccess(
			state,
			action: PayloadAction<BacktestConfigDto>
		) {
			state.backtestConfigLoading = false;
			state.backtestConfig = action.payload;
		},
		fetchBacktestConfigFailure(state) {
			state.backtestConfigLoading = false;
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
		executeRunFailure(state, action: PayloadAction<number>) {
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
		stopRunFailure(_state, _action: PayloadAction<void>) {},
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
		invalidateRunFailure(state) {
			state.invalidatingRunId = null;
		},
	},
});

export const {
	fetchBacktestsRequest,
	fetchBacktestsSuccess,
	fetchBacktestsFailure,
	fetchBacktestRequest,
	fetchBacktestSuccess,
	fetchBacktestFailure,
	createBacktestRequest,
	createBacktestSuccess,
	createBacktestFailure,
	clearLastCreatedId,
	updateBacktestRequest,
	updateBacktestSuccess,
	updateBacktestFailure,
	deleteBacktestRequest,
	deleteBacktestSuccess,
	deleteBacktestFailure,
	fetchRunsRequest,
	fetchRunsSuccess,
	fetchRunsFailure,
	createRunRequest,
	createRunSuccess,
	createRunFailure,
	cloneRunRequest,
	updateRunRequest,
	updateRunSuccess,
	deleteRunRequest,
	deleteRunSuccess,
	deleteRunFailure,
	executeRunRequest,
	executeRunSuccess,
	executeRunFailure,
	stopRunRequest,
	stopRunSuccess,
	stopRunFailure,
	invalidateRunRequest,
	invalidateRunSuccess,
	invalidateRunFailure,
	fetchRunDetailRequest,
	fetchRunDetailSuccess,
	fetchRunDetailFailure,
	fetchRunWeightsRequest,
	fetchRunWeightsSuccess,
	fetchRunWeightsFailure,
	fetchBacktestConfigRequest,
	fetchBacktestConfigSuccess,
	fetchBacktestConfigFailure,
} = slice.actions;

export default slice.reducer;
