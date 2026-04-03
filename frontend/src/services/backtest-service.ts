import { api } from './api';

export type BacktestStatus = "READY" | "RUNNING" | "DONE" | "ERROR" | "STOPPED";

export type BacktestDto = {
	id: number;
	name: string;
	description: string | null;
	strategy_version: string;
	frequency: string;
	created_at: string;
	updated_at: string;
};

export type InitialAllocation = "target" | "neutral";

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
	parameters: Record<string, string>;
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

export const getBacktestConfigApi = async (backtestId: number): Promise<BacktestConfigDto> => {
	const res = await api.get(`/backtests/${backtestId}/config`);
	return res.data;
};

export const patchAllocationParameterApi = async (key: string, value: number): Promise<void> => {
	await api.patch(`/allocation-config/parameters/${key}`, { value });
};

export const invalidateRunApi = async (backtestId: number, runId: number): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/invalidate`);
};

// Backtests (container)
export const listBacktestsApi = async (page = 1, limit = 20): Promise<BacktestListResponse> => {
	const res = await api.get('/backtests', { params: { page, limit } });
	return res.data;
};

export const getBacktestApi = async (id: number): Promise<BacktestDto> => {
	const res = await api.get(`/backtests/${id}`);
	return res.data;
};

export const createBacktestApi = async (payload: CreateBacktestPayload): Promise<{ id: number }> => {
	const res = await api.post('/backtests', payload);
	return res.data;
};

export const updateBacktestApi = async (id: number, payload: { name?: string; description?: string }): Promise<void> => {
	await api.patch(`/backtests/${id}`, payload);
};

export const deleteBacktestApi = async (id: number): Promise<void> => {
	await api.delete(`/backtests/${id}`);
};

// Runs
export const listRunsApi = async (backtestId: number): Promise<BacktestRunDto[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs`);
	return res.data;
};

export const createRunApi = async (backtestId: number, payload: CreateRunPayload): Promise<{ id: number }> => {
	const res = await api.post(`/backtests/${backtestId}/create-run`, payload);
	return res.data;
};

export const deleteRunApi = async (backtestId: number, runId: number): Promise<void> => {
	await api.delete(`/backtests/${backtestId}/runs/${runId}`);
};

export const executeRunApi = async (backtestId: number, runId: number): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/execute`);
};

export const stopRunApi = async (backtestId: number, runId: number): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/stop`);
};

export const getRunApi = async (backtestId: number, runId: number): Promise<BacktestRunDto> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}`);
	return res.data;
};

export const updateRunApi = async (backtestId: number, runId: number, payload: { name?: string; start?: string; end?: string; parameters?: Record<string, string> }): Promise<void> => {
	await api.patch(`/backtests/${backtestId}/runs/${runId}`, payload);
};

export const cloneRunApi = async (backtestId: number, runId: number): Promise<BacktestRunDto> => {
	const res = await api.post(`/backtests/${backtestId}/runs/${runId}/clone`);
	return res.data;
};

export const getRunNavApi = async (backtestId: number, runId: number): Promise<{ date: string; nav: number; monthly_return: number }[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/nav`);
	return res.data;
};

export type RunWeightDto = {
	date: string;
	asset: string;
	weight: number;
	pillar_scores: string | null; // JSON string: {"Growth": "expansion", ...}
};

export const getRunWeightsApi = async (backtestId: number, runId: number): Promise<RunWeightDto[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/weights`);
	return res.data;
};
