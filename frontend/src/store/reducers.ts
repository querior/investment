import { combineReducers } from 'redux';
import scenarios from '../features/scenario/reducer';
import auth from '../features/auth/reducer';

// ================|| COMBINE REDUCERS ||============================== //
const reducers = combineReducers({
  scenarios,
  auth,
});

export type RootState = ReturnType<typeof reducers>;

export default reducers;
