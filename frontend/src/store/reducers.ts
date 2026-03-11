import { combineReducers } from 'redux';
import scenarios from '../features/scenario/reducer';
import auth from '../features/auth/reducer';
import data from '../features/data/reducer';

// ================|| COMBINE REDUCERS ||============================== //
const reducers = combineReducers({
  scenarios,
  auth,
  data,
});

export type RootState = ReturnType<typeof reducers>;

export default reducers;
