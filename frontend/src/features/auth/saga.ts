import { call, put, takeLatest } from 'redux-saga/effects';
import { loginApi } from '../../services/auth-service';
import { setAuthToken } from '../../services/api';
import { loginRequest, loginSuccess, loginFailure, logout } from './reducer';

function* loginWorker(action: ReturnType<typeof loginRequest>): any {
  try {
    const { email, password } = action.payload;
    const data = yield call(loginApi, email, password);

    localStorage.setItem('token', data.access_token);
    setAuthToken(data.access_token);

    yield put(loginSuccess(data.access_token));

    // redirect to home
    window.location.href = '/';
  } catch (e: any) {
    const msg = e?.response?.data?.detail ?? 'Login failed';
    yield put(loginFailure(msg));
  }
}

function* logoutWorker(): any {
  localStorage.removeItem('token');
  setAuthToken(null);
  // redirect to login
  window.location.href = '/login';
}

export function* authWatcher() {
  yield takeLatest(loginRequest.type, loginWorker);
  yield takeLatest(logout.type, logoutWorker);
}
