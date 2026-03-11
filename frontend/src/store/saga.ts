import { all, fork } from 'redux-saga/effects';
import { scenarioWatcher } from '../features/scenario/saga';
import { authWatcher } from '../features/auth/saga';

export const rootSaga = function* root() {
  yield all([
    fork(scenarioWatcher),
    fork(authWatcher),
  ]);
};
