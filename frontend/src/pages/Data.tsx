import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
	Input,
	Modal,
	notification,
	Radio,
	Table,
	Tabs,
	Tooltip,
	Typography,
	Alert,
	Collapse,
} from "antd";
import { EyeOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
	fetchCatalogRequest,
	ingestRequest,
	SeriesEntry,
	type CatalogCategory,
	type IngestMode,
} from "../features/data/reducer";
import { RootState } from "../store/reducers";

const { Title } = Typography;

const buildColumns = (
	onView: (id: string) => void,
	onRefresh: (record: SeriesEntry) => void
): ColumnsType<SeriesEntry> => [
	{
		title: "Symbol",
		dataIndex: "symbol",
		key: "symbol",
		width: 140,
		render: (v) => <span className="font-mono font-semibold">{v}</span>,
	},
	{
		title: "Description",
		key: "description",
		render: (_, record) => (
			<div>
				<div>{record.description}</div>
				{record.formula && (
					<div className="text-xs text-gray-400 font-mono mt-0.5">
						{record.formula}
					</div>
				)}
			</div>
		),
	},
	{
		title: "Frequency",
		dataIndex: "frequency",
		key: "frequency",
		width: 100,
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
	const { catalog, loading, filter, ingestLoading, lastIngestResult, error } =
		useSelector((s: RootState) => s.data);
	const [activeTab, setActiveTab] = useState<CatalogCategory>("macro_raw");
	const [page, setPage] = useState(1);
	const PAGE_SIZE = 10;
	const [ingestModal, setIngestModal] = useState<{
		open: boolean;
		record: SeriesEntry | null;
	}>({ open: false, record: null });
	const [ingestMode, setIngestMode] = useState<IngestMode>("delta");

	const prevIngestLoading = useRef(false);
	useEffect(() => {
		if (prevIngestLoading.current && !ingestLoading) {
			if (error) {
				notification.error({
					message: "Ingestion fallita",
					description: error,
				});
			} else if (lastIngestResult) {
				notification.success({
					message: "Ingestion completata",
					description: lastIngestResult.detail,
				});
			}
		}
		prevIngestLoading.current = ingestLoading;
	}, [ingestLoading, error, lastIngestResult]);

	const totalForTab = catalog.counters[activeTab];

	const openIngestModal = (record: SeriesEntry) => {
		setIngestMode("delta");
		setIngestModal({ open: true, record });
	};

	const handleIngestConfirm = () => {
		if (!ingestModal.record) return;
		dispatch(
			ingestRequest({ symbol: ingestModal.record.symbol, mode: ingestMode })
		);
		setIngestModal({ open: false, record: null });
	};

	const columns = buildColumns(
		(id) => navigate(`/analysis/data/${id}`),
		(record) => openIngestModal(record)
	);

	const fetchCatalog = (
		category: CatalogCategory,
		p: number,
		filterValue?: string
	) => {
		dispatch(
			fetchCatalogRequest({
				page: p,
				limit: PAGE_SIZE,
				data_category: category,
				orderBy: "symbol",
				filter: filterValue,
			})
		);
	};

	const handleSearch = (value: string) => {
		setPage(1);
		fetchCatalog(activeTab, 1, value);
	};

	const handleTabChange = (key: string) => {
		const category = key as CatalogCategory;
		setActiveTab(category);
		setPage(1);
		fetchCatalog(category, 1, filter);
	};

	const handlePageChange = (newPage: number) => {
		setPage(newPage);
		fetchCatalog(activeTab, newPage, filter);
	};

	const tabs = [
		{ key: "macro_raw", label: `Macro Raw (${catalog.counters.macro_raw})` },
		{
			key: "macro_processed",
			label: `Macro Processed (${catalog.counters.macro_processed})`,
		},
		{ key: "pillars", label: `Pillars (${catalog.counters.pillars})` },
		{ key: "market", label: `Market (${catalog.counters.market})` },
	];

	useEffect(() => {
		fetchCatalog("macro_raw", 1);
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
				onChange={(e: ChangeEvent<HTMLInputElement>) =>
					handleSearch(e.target.value)
				}
				allowClear
				className="max-w-sm"
			/>

			<Tabs activeKey={activeTab} onChange={handleTabChange} items={tabs} />

			{activeTab === "macro_processed" && (
				<Collapse
					size="small"
					ghost
					items={[
						{
							key: "formula",
							label: "Come vengono processati i dati raw?",
							children: (
								<div className="space-y-2 text-sm text-gray-700">
									<p>
										Ogni serie raw viene trasformata e normalizzata in due
										passaggi:
									</p>
									<ol className="list-decimal list-inside space-y-1 pl-2">
										<li>
											<strong>Trasformazione</strong>
											<ul className="list-disc list-inside pl-4 mt-1 space-y-1 text-gray-600">
												<li>
													<code>yoy</code> — variazione anno su anno:{" "}
													<code>(xₜ / xₜ₋₁₂ − 1) × 100</code>
												</li>
												<li>
													<code>level</code> — variazione mensile assoluta:{" "}
													<code>xₜ − xₜ₋₁</code>
												</li>
											</ul>
										</li>
										<li>
											<strong>Z-score rolling</strong> su finestra di 60 mesi:{" "}
											<code>z = (x − μ) / σ</code>, clippato a ±3
										</li>
									</ol>
									<p className="text-gray-500 text-xs">
										Le prime 36 osservazioni vengono scartate (warm-up della
										rolling window).
									</p>
								</div>
							),
						},
					]}
				/>
			)}

			<Table
				rowKey="id"
				columns={columns}
				dataSource={catalog.items}
				loading={loading}
				locale={{ emptyText: "No data available" }}
				pagination={{
					current: page,
					pageSize: PAGE_SIZE,
					total: totalForTab,
					showSizeChanger: false,
					onChange: handlePageChange,
				}}
				size="small"
			/>

			<Modal
				title={`Ingest — ${ingestModal.record?.symbol ?? ""}`}
				open={ingestModal.open}
				onOk={handleIngestConfirm}
				onCancel={() => setIngestModal({ open: false, record: null })}
				okText="Avvia"
				cancelText="Annulla"
				confirmLoading={ingestLoading}
			>
				{ingestModal.record?.data_category === "macro_raw" ||
				ingestModal.record?.data_category === "market" ? (
					<Radio.Group
						value={ingestMode}
						onChange={(e) => setIngestMode(e.target.value)}
						className="flex flex-col gap-2 mt-2"
					>
						<Radio value="delta">
							Delta — solo dati mancanti dall'ultima data
						</Radio>
						<Radio value="full">Full — scarica l'intera serie storica</Radio>
					</Radio.Group>
				) : (
					<Alert
						type="info"
						showIcon
						message="Ricalcolo serie derivata"
						description={`La serie "${ingestModal.record?.symbol}" verrà ricalcolata a partire dai dati raw di origine.`}
						className="mt-2"
					/>
				)}
			</Modal>
		</div>
	);
}
