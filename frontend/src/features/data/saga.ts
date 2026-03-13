import { call, put, takeLatest } from "redux-saga/effects";
import { getCatalogApi, getSeriesForSymbolApi } from "../../services/data-service";
import {
	fetchCatalogSuccess,
	fetchCatalogFailure,
	fetchCatalogRequest,
	getSeriesForSymbolRequest,
	getSeriesForSymbolSuccess,
	getSeriesForSymbolFailed,
} from "./reducer";

function* fetchCatalogEffect(
	action: ReturnType<typeof fetchCatalogRequest>
): any {
	try {
		const catalog = yield call(getCatalogApi, action.payload);
		yield put(fetchCatalogSuccess(catalog));
	} catch (e: any) {
		const status = e?.response?.status;
		if (status === 404) {
			yield put(
				fetchCatalogSuccess({
					items: [],
					active_category: action.payload.data_category,
					counters: {
						raw: 0,
						pillars: 0,
					},
				})
			);
		} else {
			const msg =
				e?.response?.data?.detail ?? "Impossibile caricare il catalogo";
			yield put(fetchCatalogFailure(msg));
		}
	}
}

function* getSeriesForSymbolEffect(
	action: ReturnType<typeof getSeriesForSymbolRequest>
): any {
	try {
		const series = yield call(getSeriesForSymbolApi, action.payload);
		yield put(getSeriesForSymbolSuccess(series));
	} catch (e: any) {
		const msg = e?.response?.data?.detail ?? "Impossibile caricare la serie";
		yield put(getSeriesForSymbolFailed(msg));
	}
}

export function* dataWatcher() {
	yield takeLatest(fetchCatalogRequest.type, fetchCatalogEffect);
	yield takeLatest(getSeriesForSymbolRequest.type, getSeriesForSymbolEffect);
}
