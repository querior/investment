import { call, put, takeLatest } from "redux-saga/effects";
import {
	listBacktestsApi,
	createBacktestApi,
	updateBacktestApi,
	deleteBacktestApi,
	getBacktestApi,
	listRunsApi,
	createRunApi,
	deleteRunApi,
	executeRunApi,
	stopRunApi,
	getRunApi,
	getRunStatusApi,
	getRunWeightsApi,
	updateRunApi,
	getBacktestConfigApi,
	getRunNavApi,
	invalidateRunApi,
	cloneRunApi,
	getPortfolioPerformancesApi,
} from "../../services/backtest-service";
import {
	fetchBacktestsRequest,
	fetchBacktestsSuccess,
	fetchBacktestRequest,
	fetchBacktestSuccess,
	createBacktestRequest,
	createBacktestSuccess,
	updateBacktestRequest,
	updateBacktestSuccess,
	deleteBacktestRequest,
	deleteBacktestSuccess,
	fetchRunsRequest,
	fetchRunsSuccess,
	createRunRequest,
	createRunSuccess,
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
	fetchRunStatusRequest,
	fetchRunStatusSuccess,
	fetchRunWeightsRequest,
	fetchRunWeightsSuccess,
	fetchRunNavRequest,
	fetchRunNavSuccess,
	fetchPortfolioPerformanceRequest,
	fetchPortfolioPerformanceSuccess,
	fetchBacktestConfigRequest,
	fetchBacktestConfigSuccess,
	cloneRunRequest,
	backtestActionFailure,
} from "./reducer";

function* fetchBacktestsEffect(
	action: ReturnType<typeof fetchBacktestsRequest>
): any {
	try {
		const { page, limit } = action.payload ?? {};
		const data = yield call(listBacktestsApi, page, limit);
		yield put(fetchBacktestsSuccess(data));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to load backtests"
			)
		);
	}
}

function* fetchBacktestEffect(
	action: ReturnType<typeof fetchBacktestRequest>
): any {
	try {
		const bt = yield call(getBacktestApi, action.payload);
		yield put(fetchBacktestSuccess(bt));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to load backtest"
			)
		);
	}
}

function* createBacktestEffect(
	action: ReturnType<typeof createBacktestRequest>
): any {
	try {
		const { id } = yield call(createBacktestApi, action.payload);
		yield put(createBacktestSuccess(id));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to create backtest"
			)
		);
	}
}

function* updateBacktestEffect(
	action: ReturnType<typeof updateBacktestRequest>
): any {
	const { id, ...payload } = action.payload;
	try {
		yield call(updateBacktestApi, id, payload);
		yield put(updateBacktestSuccess(id));
		yield put(fetchBacktestsRequest());
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to update backtest"
			)
		);
	}
}

function* deleteBacktestEffect(
	action: ReturnType<typeof deleteBacktestRequest>
): any {
	const id = action.payload;
	try {
		yield call(deleteBacktestApi, id);
		yield put(deleteBacktestSuccess(id));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to update backtest"
			)
		);
	}
}

function* fetchRunsEffect(action: ReturnType<typeof fetchRunsRequest>): any {
	try {
		const runs = yield call(listRunsApi, action.payload);
		yield put(fetchRunsSuccess(runs));
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to load runs")
		);
	}
}

function* createRunEffect(action: ReturnType<typeof createRunRequest>): any {
	const { backtestId, payload } = action.payload;
	try {
		const { id } = yield call(createRunApi, backtestId, payload);
		// fetch the full run object to get all fields
		const runs = yield call(listRunsApi, backtestId);
		const created = runs.find((r: any) => r.id === id);
		yield put(createRunSuccess(created));
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to create run")
		);
	}
}

function* cloneRunEffect(action: ReturnType<typeof cloneRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		const { id } = yield call(cloneRunApi, backtestId, runId);
		// fetch the full run object to get all fields
		const runs = yield call(listRunsApi, backtestId);
		const created = runs.find((r: any) => r.id === id);
		yield put(createRunSuccess(created));
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to create run")
		);
	}
}

function* updateRunEffect(action: ReturnType<typeof updateRunRequest>): any {
	const { backtestId, runId, patch } = action.payload;
	try {
		yield call(updateRunApi, backtestId, runId, patch);
		yield put(updateRunSuccess({ runId, patch }));
	} catch {}
}

function* deleteRunEffect(action: ReturnType<typeof deleteRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(deleteRunApi, backtestId, runId);
		yield put(deleteRunSuccess(runId));
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to delete run")
		);
	}
}

function* executeRunEffect(action: ReturnType<typeof executeRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		// Avvia in background (202) — ritorna subito
		const response: { id: number; status: string } = yield call(
			executeRunApi,
			backtestId,
			runId
		);
		yield put(
			executeRunSuccess({ runId: response.id, status: response.status })
		);
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to exec run")
		);
	}
}

function* stopRunEffect(action: ReturnType<typeof stopRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(stopRunApi, backtestId, runId);
		yield put(stopRunSuccess());
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to stop run")
		);
	}
}

function* invalidateRunEffect(
	action: ReturnType<typeof invalidateRunRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(invalidateRunApi, backtestId, runId);
		yield put(invalidateRunSuccess(runId));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to invalidate run"
			)
		);
	}
}

function* fetchRunDetailEffect(
	action: ReturnType<typeof fetchRunDetailRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		const run = yield call(getRunApi, backtestId, runId);
		yield put(fetchRunDetailSuccess(run));
	} catch (e: any) {
		yield put(
			backtestActionFailure(e?.response?.data?.detail ?? "Failed to load run")
		);
	}
}

function* fetchRunWeightsEffect(
	action: ReturnType<typeof fetchRunWeightsRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		const weights = yield call(getRunWeightsApi, backtestId, runId);
		yield put(fetchRunWeightsSuccess(weights));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to load weights"
			)
		);
	}
}

function* fetchBacktestConfigEffect(
	action: ReturnType<typeof fetchBacktestConfigRequest>
): any {
	try {
		const config = yield call(getBacktestConfigApi, action.payload);
		yield put(fetchBacktestConfigSuccess(config));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to load backtest config"
			)
		);
	}
}

function* fetchRunNavEffect(
	action: ReturnType<typeof fetchRunNavRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		const navData = yield call(getRunNavApi, backtestId, runId);
		yield put(fetchRunNavSuccess(navData));
	} catch (e: any) {
		// Silently fail for nav polling — don't show error
		// Nav is auxiliary data and polling failures shouldn't interrupt UX
	}
}

function* fetchRunStatusEffect(
	action: ReturnType<typeof fetchRunStatusRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		const status = yield call(getRunStatusApi, backtestId, runId);
		yield put(fetchRunStatusSuccess(status));
	} catch (e: any) {
		// Silently fail for status polling — don't show error
	}
}

function* fetchPortfolioPerformancesEffect(
	action: ReturnType<typeof fetchPortfolioPerformanceRequest>
): any {
	const { backtestId, runId, page = 1, limit = 20 } = action.payload;
	try {
		const data = yield call(
			getPortfolioPerformancesApi,
			backtestId,
			runId,
			page,
			limit
		);
		yield put(fetchPortfolioPerformanceSuccess(data));
	} catch (e: any) {
		yield put(
			backtestActionFailure(
				e?.response?.data?.detail ?? "Failed to load portfolio performance"
			)
		);
	}
}

export function* backtestWatcher() {
	yield takeLatest(fetchBacktestsRequest.type, fetchBacktestsEffect);
	yield takeLatest(fetchBacktestRequest.type, fetchBacktestEffect);
	yield takeLatest(createBacktestRequest.type, createBacktestEffect);
	yield takeLatest(updateBacktestRequest.type, updateBacktestEffect);
	yield takeLatest(deleteBacktestRequest.type, deleteBacktestEffect);
	yield takeLatest(fetchRunsRequest.type, fetchRunsEffect);
	yield takeLatest(createRunRequest.type, createRunEffect);
	yield takeLatest(cloneRunRequest.type, cloneRunEffect);
	yield takeLatest(updateRunRequest.type, updateRunEffect);
	yield takeLatest(deleteRunRequest.type, deleteRunEffect);
	yield takeLatest(executeRunRequest.type, executeRunEffect);
	yield takeLatest(stopRunRequest.type, stopRunEffect);
	yield takeLatest(invalidateRunRequest.type, invalidateRunEffect);
	yield takeLatest(fetchRunDetailRequest.type, fetchRunDetailEffect);
	yield takeLatest(fetchRunStatusRequest.type, fetchRunStatusEffect);
	yield takeLatest(fetchRunWeightsRequest.type, fetchRunWeightsEffect);
	yield takeLatest(fetchRunNavRequest.type, fetchRunNavEffect);
	yield takeLatest(
		fetchPortfolioPerformanceRequest.type,
		fetchPortfolioPerformancesEffect
	);
	yield takeLatest(fetchBacktestConfigRequest.type, fetchBacktestConfigEffect);
}
