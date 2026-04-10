import { call, delay, put, select, takeLatest } from "redux-saga/effects";
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
	updateRunApi,
	getBacktestConfigApi,
	invalidateRunApi,
	cloneRunApi,
	getPortfolioPerformancesApi,
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
	fetchPortfolioPerformanceRequest,
	fetchPortfolioPerformanceSuccess,
	fetchPortfolioPerformanceFailure,
	fetchBacktestConfigRequest,
	fetchBacktestConfigSuccess,
	fetchBacktestConfigFailure,
	cloneRunRequest,
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
			fetchBacktestsFailure(
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
			fetchBacktestFailure(
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
			createBacktestFailure(
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
		yield put(updateBacktestFailure(id));
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
		yield put(deleteBacktestFailure(id));
	}
}

function* fetchRunsEffect(action: ReturnType<typeof fetchRunsRequest>): any {
	try {
		const runs = yield call(listRunsApi, action.payload);
		yield put(fetchRunsSuccess(runs));
	} catch (e: any) {
		yield put(
			fetchRunsFailure(e?.response?.data?.detail ?? "Failed to load runs")
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
			createRunFailure(e?.response?.data?.detail ?? "Failed to create run")
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
			createRunFailure(e?.response?.data?.detail ?? "Failed to create run")
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

			// Prendi il backtest dal reducer per sapere la frequency
			const state: any = yield select();
			const backtest = state.backtest.current;

			// Carica i dati corretti in base al tipo di backtest
			if (backtest?.frequency === "EOM") {
				// LONG: carica i pesi
				try {
					const weights = yield call(getRunWeightsApi, backtestId, runId);
					yield put(fetchRunWeightsSuccess(weights));
				} catch {}
			} else if (backtest?.frequency === "EOD") {
				// OPTION/SHORT: carica le performances
				yield put(
					fetchPortfolioPerformanceRequest({
						backtestId,
						runId,
						page: 1,
						limit: 20,
					})
				);
			}

			if (run.status !== "RUNNING") break;
		}

		// Fetch finale ritardato per assicurarsi che i metriche siano calcolati
		yield delay(1000);
		try {
			const finalRun = yield call(getRunApi, backtestId, runId);
			yield put(fetchRunDetailSuccess(finalRun));
		} catch {}

		yield put(executeRunSuccess(runId));
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

function* invalidateRunEffect(
	action: ReturnType<typeof invalidateRunRequest>
): any {
	const { backtestId, runId } = action.payload;
	try {
		yield call(invalidateRunApi, backtestId, runId);
		yield put(invalidateRunSuccess(runId));
	} catch {
		yield put(invalidateRunFailure());
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
			fetchRunDetailFailure(e?.response?.data?.detail ?? "Failed to load run")
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
			fetchRunWeightsFailure(
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
	} catch {
		yield put(fetchBacktestConfigFailure());
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
			fetchPortfolioPerformanceFailure(
				e?.response?.data?.detail ?? "Failed to load portfolio performances"
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
	yield takeLatest(fetchRunWeightsRequest.type, fetchRunWeightsEffect);
	yield takeLatest(
		fetchPortfolioPerformanceRequest.type,
		fetchPortfolioPerformancesEffect
	);
	yield takeLatest(fetchBacktestConfigRequest.type, fetchBacktestConfigEffect);
}
