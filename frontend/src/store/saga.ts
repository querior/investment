import { all, fork } from 'redux-saga/effects';
import { scenarioWatcher } from '../features/scenario/saga';
import { authWatcher } from '../features/auth/saga';
import { dataWatcher } from '../features/data/saga';
import { backtestWatcher } from '../features/backtest/saga';

export const rootSaga = function* root() {
  yield all([
    fork(scenarioWatcher),
    fork(authWatcher),
    fork(dataWatcher),
    fork(backtestWatcher),
  ]);
};
