import { call, put, takeLatest } from 'redux-saga/effects';
import { listScenariosApi } from '../../services/scenario-service';
import { fetchScenarios, fetchScenariosSuccess, fetchScenariosFailure } from './reducer';

function* fetchWorker(): any {
  try {
    const items = yield call(listScenariosApi);
    yield put(fetchScenariosSuccess(items));
  } catch (e: any) {
    const msg = e?.response?.data?.detail ?? 'Fetch scenarios failed';
    yield put(fetchScenariosFailure(msg));
  }
}

export function* scenarioWatcher() {
  yield takeLatest(fetchScenarios.type, fetchWorker);
}
