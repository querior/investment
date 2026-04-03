import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type DataCategory =
	| "macro_raw"
	| "macro_processed"
	| "pillar"
	| "market";
export type CatalogCategory =
	| "macro_raw"
	| "macro_processed"
	| "pillars"
	| "market";

export type SeriesEntry = {
	id: string;
	symbol: string;
	description: string;
	formula: string | null;
	source: string;
	frequency: string;
	first_date: string | null;
	last_date: string | null;
	row_count: number;
	data_category: DataCategory;
};

export type Catalog = {
	items: SeriesEntry[];
	active_category: CatalogCategory;
	counters: {
		macro_raw: number;
		macro_processed: number;
		pillars: number;
		market: number;
	};
};

export type SeriesPoint = {
	date: string;
	value: number;
	regime?: string;
};

export type SeriesDetail = {
	symbol: string;
	description: string;
	source: string;
	frequency: string;
	first_date: string | null;
	last_date: string | null;
	row_count: number;
	data_category: DataCategory;
	points: SeriesPoint[];
};

export type IngestMode = "delta" | "full";

export type IngestResult = {
	symbol: string;
	mode: string;
	inserted: number | null;
	detail: string;
};

export type DataState = {
	catalog: Catalog;
	filter?: string;
	loading: boolean;
	error: string | null;
	currentSeries: SeriesDetail | null;
	ingestLoading: boolean;
	lastIngestResult: IngestResult | null;
};

const initialState: DataState = {
	catalog: {
		items: [],
		active_category: "macro_raw",
		counters: {
			macro_raw: 0,
			macro_processed: 0,
			pillars: 0,
			market: 0,
		},
	},
	loading: false,
	error: null,
	currentSeries: null,
	ingestLoading: false,
	lastIngestResult: null,
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
				data_category: CatalogCategory;
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
		ingestRequest(
			state,
			_action: PayloadAction<{ symbol: string; mode: IngestMode }>
		) {
			state.ingestLoading = true;
			state.error = null;
		},
		ingestSuccess(state, action: PayloadAction<IngestResult>) {
			state.ingestLoading = false;
			state.lastIngestResult = action.payload;
		},
		ingestFailure(state, action: PayloadAction<string>) {
			state.ingestLoading = false;
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
	ingestRequest,
	ingestSuccess,
	ingestFailure,
} = slice.actions;
export default slice.reducer;
