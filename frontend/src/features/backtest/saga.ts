import { call, delay, put, takeLatest } from "redux-saga/effects";
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
	getRunWeightsApi,
} from "../../services/backtest-service";
import {
	fetchBacktestsRequest,
	fetchBacktestsSuccess,
	fetchBacktestsFailure,
	fetchBacktestRequest,
	fetchBacktestSuccess,
	fetchBacktestFailure,
	createBacktestRequest,
	createBacktestSuccess,
	createBacktestFailure,
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
	deleteRunRequest,
	deleteRunSuccess,
	deleteRunFailure,
	executeRunRequest,
	executeRunSuccess,
	executeRunFailure,
	stopRunRequest,
	stopRunSuccess,
	stopRunFailure,
	fetchRunDetailRequest,
	fetchRunDetailSuccess,
	fetchRunDetailFailure,
	fetchRunWeightsRequest,
	fetchRunWeightsSuccess,
	fetchRunWeightsFailure,
} from "./reducer";

function* fetchBacktestsEffect(action: ReturnType<typeof fetchBacktestsRequest>): any {
	try {
		const { page, limit } = action.payload ?? {};
		const data = yield call(listBacktestsApi, page, limit);
		yield put(fetchBacktestsSuccess(data));
	} catch (e: any) {
		yield put(fetchBacktestsFailure(e?.response?.data?.detail ?? "Failed to load backtests"));
	}
}

function* fetchBacktestEffect(action: ReturnType<typeof fetchBacktestRequest>): any {
	try {
		const bt = yield call(getBacktestApi, action.payload);
		yield put(fetchBacktestSuccess(bt));
	} catch (e: any) {
		yield put(fetchBacktestFailure(e?.response?.data?.detail ?? "Failed to load backtest"));
	}
}

function* createBacktestEffect(action: ReturnType<typeof createBacktestRequest>): any {
	try {
		const { id } = yield call(createBacktestApi, action.payload);
		yield put(createBacktestSuccess(id));
	} catch (e: any) {
		yield put(createBacktestFailure(e?.response?.data?.detail ?? "Failed to create backtest"));
	}
}

function* updateBacktestEffect(action: ReturnType<typeof updateBacktestRequest>): any {
	const { id, ...payload } = action.payload;
	try {
		yield call(updateBacktestApi, id, payload);
		yield put(updateBacktestSuccess(id));
		yield put(fetchBacktestsRequest());
	} catch (e: any) {
		yield put(updateBacktestFailure(id));
	}
}

function* deleteBacktestEffect(action: ReturnType<typeof deleteBacktestRequest>): any {
	const id = action.payload;
	try {
		yield call(deleteBacktestApi, id);
		yield put(deleteBacktestSuccess(id));
	} catch (e: any) {
		yield put(deleteBacktestFailure(id));
	}
}

function* fetchRunsEffect(action: ReturnType<typeof fetchRunsRequest>): any {
	try {
		const runs = yield call(listRunsApi, action.payload);
		yield put(fetchRunsSuccess(runs));
	} catch (e: any) {
		yield put(fetchRunsFailure(e?.response?.data?.detail ?? "Failed to load runs"));
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
		yield put(createRunFailure(e?.response?.data?.detail ?? "Failed to create run"));
	}
}

function* deleteRunEffect(action: ReturnType<typeof deleteRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(deleteRunApi, backtestId, runId);
		yield put(deleteRunSuccess(runId));
	} catch (e: any) {
		yield put(deleteRunFailure(runId));
	}
}

function* executeRunEffect(action: ReturnType<typeof executeRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		// Avvia in background (202) — ritorna subito
		yield call(executeRunApi, backtestId, runId);

		// Polling ogni 2s finché status != RUNNING
		while (true) {
			yield delay(2000);
			const run = yield call(getRunApi, backtestId, runId);
			yield put(fetchRunDetailSuccess(run));
			try {
				const weights = yield call(getRunWeightsApi, backtestId, runId);
				yield put(fetchRunWeightsSuccess(weights));
			} catch {}
			if (run.status !== "RUNNING") break;
		}

		yield put(executeRunSuccess(runId));
		const runs = yield call(listRunsApi, backtestId);
		yield put(fetchRunsSuccess(runs));
	} catch (e: any) {
		yield put(executeRunFailure(runId));
	}
}

function* stopRunEffect(action: ReturnType<typeof stopRunRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(stopRunApi, backtestId, runId);
		yield put(stopRunSuccess());
	} catch (e: any) {
		yield put(stopRunFailure());
	}
}

function* fetchRunDetailEffect(action: ReturnType<typeof fetchRunDetailRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		const run = yield call(getRunApi, backtestId, runId);
		yield put(fetchRunDetailSuccess(run));
	} catch (e: any) {
		yield put(fetchRunDetailFailure(e?.response?.data?.detail ?? "Failed to load run"));
	}
}

function* fetchRunWeightsEffect(action: ReturnType<typeof fetchRunWeightsRequest>): any {
	const { backtestId, runId } = action.payload;
	try {
		const weights = yield call(getRunWeightsApi, backtestId, runId);
		yield put(fetchRunWeightsSuccess(weights));
	} catch (e: any) {
		yield put(fetchRunWeightsFailure(e?.response?.data?.detail ?? "Failed to load weights"));
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
	yield takeLatest(deleteRunRequest.type, deleteRunEffect);
	yield takeLatest(executeRunRequest.type, executeRunEffect);
	yield takeLatest(stopRunRequest.type, stopRunEffect);
	yield takeLatest(fetchRunDetailRequest.type, fetchRunDetailEffect);
	yield takeLatest(fetchRunWeightsRequest.type, fetchRunWeightsEffect);
}
