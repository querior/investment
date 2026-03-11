import { api } from "./api";
import { Catalog } from "../features/data/reducer";

export async function getCatalogApi(params: {
	page: number;
	limit: number;
	data_category: "raw" | "pillars";
	orderBy: string;
	filter: string | undefined;
}): Promise<Catalog> {
	const { page, limit, data_category, orderBy, filter } = params;
	const res = await api.get<Catalog>(
		`/data/catalog?page=${page}&limit=${limit}&data_category=${data_category}&orderBy=${orderBy}&filter=${filter}`
	);
	return res.data;
}
