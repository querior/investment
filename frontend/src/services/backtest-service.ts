import { api } from './api';

export type BacktestStatus = "READY" | "RUNNING" | "DONE" | "ERROR" | "STOPPED";

export type BacktestDto = {
	id: number;
	name: string;
	description: string | null;
	strategy_version: string;
	frequency: string;
	primary_index: string;
	created_at: string;
	updated_at: string;
};

export type BacktestRunDto = {
	id: number;
	backtest_id: number;
	start_date: string;
	end_date: string;
	frequency: string;
	primary_index: string;
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
	primary_index?: string;
};

export type CreateRunPayload = {
	start: string;
	end: string;
	notes?: string;
};

export type AllocationConfig = {
	sensitivity: Record<string, Record<string, number>>;
	neutral: Record<string, number>;
	scale_k: number;
	max_abs_delta: number;
	macro_score_weights: Record<string, number>;
};

export const getAllocationConfigApi = async (): Promise<AllocationConfig> => {
	const res = await api.get('/allocation-config');
	return res.data;
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

export const getRunNavApi = async (backtestId: number, runId: number): Promise<{ date: string; nav: number; monthly_return: number }[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/nav`);
	return res.data;
};

export type RunWeightDto = {
	date: string;
	asset: string;
	weight: number;
	macro_score: number | null;
	pillar_scores: string | null; // JSON string: {"Growth": 0.45, ...}
};

export const getRunWeightsApi = async (backtestId: number, runId: number): Promise<RunWeightDto[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/weights`);
	return res.data;
};
