import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type Scenario = {
  id: number;
  name: string;
  description: string;
  config_json: string;
  owner_email: string;
};

export type ScenarioState = {
  items: Scenario[];
  loading: boolean;
  error: string | null;
};

const initialState: ScenarioState = {
  items: [],
  loading: false,
  error: null,
};

const slice = createSlice({
  name: 'scenario',
  initialState,
  reducers: {
    fetchScenarios(state) {
      state.loading = true;
      state.error = null;
    },
    fetchScenariosSuccess(state, action: PayloadAction<Scenario[]>) {
      state.loading = false;
      state.items = action.payload;
    },
    fetchScenariosFailure(state, action: PayloadAction<string>) {
      state.loading = false;
      state.error = action.payload;
    },
  },
});

export const { fetchScenarios, fetchScenariosSuccess, fetchScenariosFailure } = slice.actions;
export default slice.reducer;
