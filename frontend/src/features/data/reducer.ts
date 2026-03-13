import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type SeriesEntry = {
	id: string;
	symbol: string;
	description: string;
	source: string;
	frequency: string;
	first_date: string | null;
	last_date: string | null;
	row_count: number;
	data_category: "raw" | "pillar";
};

export type Catalog = {
	items: SeriesEntry[];
	active_category: "raw" | "pillars";
	counters: {
		raw: number;
		pillars: number;
	};
};

export type SeriesPoint = {
	date: string;
	value: number;
};

export type SeriesDetail = {
	symbol: string;
	description: string;
	source: string;
	frequency: string;
	first_date: string | null;
	last_date: string | null;
	row_count: number;
	data_category: "raw" | "pillar";
	points: SeriesPoint[];
};

export type DataState = {
	catalog: Catalog;
	filter?: string;
	loading: boolean;
	error: string | null;
	currentSeries: SeriesDetail | null;
};

const initialState: DataState = {
	catalog: {
		items: [],
		active_category: "raw",
		counters: {
			raw: 0,
			pillars: 0,
		},
	},
	loading: false,
	error: null,
	currentSeries: null,
};

const slice = createSlice({
	name: "data",
	initialState,
	reducers: {
		fetchCatalogRequest(
			state,
			action: PayloadAction<{
				page: number;
				limit: number;
				data_category: "raw" | "pillars";
				orderBy: string;
				filter: string | undefined;
			}>
		) {
			state.loading = true;
			state.filter = action.payload.filter;
			state.error = null;
		},
		fetchCatalogSuccess(state, action: PayloadAction<Catalog>) {
			state.loading = false;
			state.catalog = action.payload;
		},
		fetchCatalogFailure(state, action: PayloadAction<string>) {
			state.loading = false;
			state.error = action.payload;
		},
		getSeriesForSymbolRequest(
			state,
			_action: PayloadAction<{
				symbol: string;
				startDate?: string;
				endDate?: string;
			}>
		) {
			state.loading = true;
			state.error = null;
			state.currentSeries = null;
		},
		getSeriesForSymbolSuccess(state, action: PayloadAction<SeriesDetail>) {
			state.loading = false;
			state.currentSeries = action.payload;
		},
		getSeriesForSymbolFailed(state, action: PayloadAction<string>) {
			state.loading = false;
			state.error = action.payload;
		},
	},
});

export const {
	fetchCatalogRequest,
	fetchCatalogSuccess,
	fetchCatalogFailure,
	getSeriesForSymbolRequest,
	getSeriesForSymbolSuccess,
	getSeriesForSymbolFailed,
} = slice.actions;
export default slice.reducer;
