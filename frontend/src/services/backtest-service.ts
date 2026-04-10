import type {
	BacktestConfigDto,
	BacktestDto,
	BacktestListResponse,
	BacktestPositionDto,
	BacktestPositionHistoryDto,
	BacktestRunDto,
	BacktestStatus,
	CreateBacktestPayload,
	CreateRunPayload,
	FrequencyType,
	RunWeightDto,
} from "../features/backtest/types";
import { api } from "./api";

export const getBacktestConfigApi = async (
	backtestId: number
): Promise<BacktestConfigDto> => {
	const res = await api.get(`/backtests/${backtestId}/config`);
	return res.data;
};

export const invalidateRunApi = async (
	backtestId: number,
	runId: number
): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/invalidate`);
};

// Backtests (container)
export const listBacktestsApi = async (
	page = 1,
	limit = 20
): Promise<BacktestListResponse> => {
	const res = await api.get("/backtests", { params: { page, limit } });
	return res.data;
};

export const getBacktestApi = async (id: number): Promise<BacktestDto> => {
	const res = await api.get(`/backtests/${id}`);
	return res.data;
};

export const createBacktestApi = async (
	payload: CreateBacktestPayload
): Promise<{ id: number }> => {
	const res = await api.post("/backtests", payload);
	return res.data;
};

export const updateBacktestApi = async (
	id: number,
	payload: { name?: string; description?: string }
): Promise<void> => {
	await api.patch(`/backtests/${id}`, payload);
};

export const deleteBacktestApi = async (id: number): Promise<void> => {
	await api.delete(`/backtests/${id}`);
};

// Runs
export const listRunsApi = async (
	backtestId: number
): Promise<BacktestRunDto[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs`);
	return res.data;
};

export const createRunApi = async (
	backtestId: number,
	payload: CreateRunPayload
): Promise<{ id: number }> => {
	const res = await api.post(`/backtests/${backtestId}/create-run`, payload);
	return res.data;
};

export const deleteRunApi = async (
	backtestId: number,
	runId: number
): Promise<void> => {
	await api.delete(`/backtests/${backtestId}/runs/${runId}`);
};

export const executeRunApi = async (
	backtestId: number,
	runId: number
): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/execute`);
};

export const stopRunApi = async (
	backtestId: number,
	runId: number
): Promise<void> => {
	await api.post(`/backtests/${backtestId}/runs/${runId}/stop`);
};

export const getRunApi = async (
	backtestId: number,
	runId: number
): Promise<BacktestRunDto> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}`);
	return res.data;
};

export const updateRunApi = async (
	backtestId: number,
	runId: number,
	payload: {
		name?: string;
		start?: string;
		end?: string;
		parameters?: Record<string, string>;
	}
): Promise<void> => {
	await api.patch(`/backtests/${backtestId}/runs/${runId}`, payload);
};

export const cloneRunApi = async (
	backtestId: number,
	runId: number
): Promise<BacktestRunDto> => {
	const res = await api.post(`/backtests/${backtestId}/runs/${runId}/clone`);
	return res.data;
};

export const getRunNavApi = async (
	backtestId: number,
	runId: number
): Promise<{ date: string; nav: number; period_return: number }[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/nav`);
	return res.data;
};

export const getRunWeightsApi = async (
	backtestId: number,
	runId: number
): Promise<RunWeightDto[]> => {
	const res = await api.get(`/backtests/${backtestId}/runs/${runId}/weights`);
	return res.data;
};

export const getPortfolioPerformancesApi = async (
	backtestId: number,
	runId: number,
	page = 1,
	limit = 20
): Promise<{
	items: BacktestPositionDto[];
	total: number;
	page: number;
	limit: number;
}> => {
	const res = await api.get(
		`/backtests/${backtestId}/runs/${runId}/positions`,
		{ params: { page, limit } }
	);
	return res.data;
};

export const getPositionHistoryApi = async (
	backtestId: number,
	runId: number,
	positionId: number
): Promise<BacktestPositionHistoryDto[]> => {
	const res = await api.get(
		`/backtests/${backtestId}/runs/${runId}/positions/${positionId}/history`
	);
	return res.data;
};
