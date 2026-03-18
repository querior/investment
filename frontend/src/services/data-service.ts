import { api } from "./api";
import { Catalog, SeriesDetail, type CatalogCategory, type IngestMode, type IngestResult } from "../features/data/reducer";

export async function getCatalogApi(params: {
	page: number;
	limit: number;
	data_category: CatalogCategory;
	orderBy: string;
	filter: string | undefined;
}): Promise<Catalog> {
	const { page, limit, data_category, orderBy, filter } = params;
	const res = await api.get<Catalog>(
		`/data/catalog?page=${page}&limit=${limit}&data_category=${data_category}&orderBy=${orderBy}&filter=${filter}`
	);
	return res.data;
}

export async function getSeriesForSymbolApi(params: {
	symbol: string;
	startDate?: string;
	endDate?: string;
}): Promise<SeriesDetail> {
	const { symbol, startDate, endDate } = params;
	const query = new URLSearchParams({ symbol });
	if (startDate) query.append("start_date", startDate);
	if (endDate) query.append("end_date", endDate);
	const res = await api.get<SeriesDetail>(`/data/series?${query.toString()}`);
	return res.data;
}

export async function ingestSeriesApi(params: {
	symbol: string;
	mode: IngestMode;
}): Promise<IngestResult> {
	const res = await api.post<IngestResult>("/ingest/series", params);
	return res.data;
}
