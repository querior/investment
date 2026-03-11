import { call, put, takeLatest } from "redux-saga/effects";
import { getCatalogApi } from "../../services/data-service";
import {
	fetchCatalogSuccess,
	fetchCatalogFailure,
	fetchCatalogRequest,
} from "./reducer";

function* fetchCatalogWorker(
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

export function* dataWatcher() {
	yield takeLatest(fetchCatalogRequest.type, fetchCatalogWorker);
}
