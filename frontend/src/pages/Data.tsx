import { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Input, Table, Tabs, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchCatalogRequest, SeriesEntry } from "../features/data/reducer";
import { RootState } from "../store/reducers";

const { Title } = Typography;

const columns: ColumnsType<SeriesEntry> = [
	{
		title: "Symbol",
		dataIndex: "symbol",
		key: "symbol",
		width: 140,
		render: (v) => <span className="font-mono font-semibold">{v}</span>,
	},
	{
		title: "Description",
		dataIndex: "description",
		key: "description",
	},
	{
		title: "Initial date",
		dataIndex: "first_date",
		key: "first_date",
		width: 120,
		render: (v) => v ?? <span className="text-gray-400">—</span>,
	},
	{
		title: "Last date",
		dataIndex: "last_date",
		key: "last_date",
		width: 120,
		render: (v) => v ?? <span className="text-gray-400">—</span>,
	},
	{
		title: "Total points",
		dataIndex: "row_count",
		key: "row_count",
		width: 120,
		align: "right",
		render: (v) => v?.toLocaleString() ?? "—",
	},
];

export default function Data() {
	const dispatch = useDispatch();
	const { catalog, loading, filter } = useSelector((s: RootState) => s.data);

	const handleSearch = (value: string) => {
		dispatch(
			fetchCatalogRequest({
				page: 1,
				limit: 10,
				data_category: catalog.active_category,
				orderBy: "symbol",
				filter: value,
			})
		);
	};

	const tabs = [
		{
			key: "raw",
			label: `Series (${catalog.counters.raw})`,
			children: (
				<Table
					rowKey="id"
					columns={columns}
					dataSource={catalog.active_category === "raw" ? catalog.items : []}
					locale={{ emptyText: "No data available" }}
					pagination={false}
					size="small"
				/>
			),
		},
		{
			key: "pillars",
			label: `Pillars (${catalog.counters.pillars})`,
			children: (
				<Table
					rowKey="id"
					columns={columns}
					dataSource={
						catalog.active_category === "pillars" ? catalog.items : []
					}
					loading={loading}
					locale={{ emptyText: "No data available" }}
					pagination={false}
					size="small"
				/>
			),
		},
	];

	useEffect(() => {
		dispatch(
			fetchCatalogRequest({
				page: 1,
				limit: 10,
				data_category: "raw",
				orderBy: "name",
				filter: undefined,
			})
		);
	}, [dispatch]);

	return (
		<div className="p-6 space-y-4">
			<Title level={3} className="!m-0">
				Data
			</Title>

			<Input
				placeholder="Cerca per ticker o descrizione…"
				prefix={<SearchOutlined className="text-gray-400" />}
				value={filter}
				onChange={(e) => handleSearch(e.target.value)}
				allowClear
				className="max-w-sm"
			/>

			<Tabs items={tabs} />
		</div>
	);
}
