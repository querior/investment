import { useEffect, useState, type ChangeEvent } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Input, Table, Tabs, Tooltip, Typography } from "antd";
import { EyeOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchCatalogRequest, SeriesEntry } from "../features/data/reducer";
import { RootState } from "../store/reducers";

const { Title } = Typography;

const buildColumns = (onView: (id: string) => void, onRefresh: (record: SeriesEntry) => void): ColumnsType<SeriesEntry> => [
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
	{
		title: "",
		key: "actions",
		width: 80,
		align: "center",
		render: (_, record) => (
			<div className="flex items-center justify-center gap-3">
				<Tooltip title="View">
					<EyeOutlined
						className="cursor-pointer text-gray-400 hover:text-blue-500"
						onClick={() => onView(record.symbol)}
					/>
				</Tooltip>
				<Tooltip title="Refresh">
					<ReloadOutlined
						className="cursor-pointer text-gray-400 hover:text-green-500"
						onClick={() => onRefresh(record)}
					/>
				</Tooltip>
			</div>
		),
	},
];

export default function Data() {
	const dispatch = useDispatch();
	const navigate = useNavigate();
	const { catalog, loading, filter } = useSelector((s: RootState) => s.data);
	const [activeTab, setActiveTab] = useState<"raw" | "pillars">("raw");

	const columns = buildColumns(
		(id) => navigate(`/analysis/data/${id}`),
		(_record) => { /* TODO: dispatch ingest refresh */ }
	);

	const fetchCatalog = (category: "raw" | "pillars", filterValue?: string) => {
		dispatch(
			fetchCatalogRequest({
				page: 1,
				limit: 10,
				data_category: category,
				orderBy: "symbol",
				filter: filterValue,
			})
		);
	};

	const handleSearch = (value: string) => fetchCatalog(activeTab, value);

	const handleTabChange = (key: string) => {
		const category = key as "raw" | "pillars";
		setActiveTab(category);
		fetchCatalog(category, filter);
	};

	const tabs = [
		{
			key: "raw",
			label: `Series (${catalog.counters.raw})`,
			children: (
				<Table
					rowKey="id"
					columns={columns}
					dataSource={activeTab === "raw" ? catalog.items : []}
					loading={loading}
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
					dataSource={activeTab === "pillars" ? catalog.items : []}
					loading={loading}
					locale={{ emptyText: "No data available" }}
					pagination={false}
					size="small"
				/>
			),
		},
	];

	useEffect(() => {
		fetchCatalog("raw");
	}, []);

	return (
		<div className="p-6 space-y-4">
			<Title level={3} className="!m-0">
				Data
			</Title>

			<Input
				placeholder="Cerca per ticker o descrizione…"
				prefix={<SearchOutlined className="text-gray-400" />}
				value={filter}
				onChange={(e: ChangeEvent<HTMLInputElement>) => handleSearch(e.target.value)}
				allowClear
				className="max-w-sm"
			/>

			<Tabs activeKey={activeTab} onChange={handleTabChange} items={tabs} />
		</div>
	);
}
