import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
	Badge,
	Button,
	Card,
	Popconfirm,
	Skeleton,
	Table,
	Tooltip,
} from "antd";
import {
	ArrowLeftOutlined,
	CopyOutlined,
	DeleteOutlined,
	EyeOutlined,
	PlusOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
	fetchBacktestRequest,
	fetchRunsRequest,
	updateRunRequest,
	deleteRunRequest,
	cloneRunRequest,
} from "../../features/backtest/reducer";
import type { RootState } from "../../store/reducers";
import type { BacktestRunDto } from "../../features/backtest/types";
import {
	BacktestStatus,
	FrequencyType,
	STATUS_BADGE,
} from "../../features/backtest/types";
import { EditableInput, EditableDateRange } from "../../components/table";
import AddBacktestRunModal from "./AddBacktestRunModal";
import { capitalize } from "../../utils/string";

export default function BacktestDetail() {
	const { id } = useParams<{ id: string }>();
	const backtestId = Number(id);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { current, currentLoading, runs, runsLoading } = useSelector(
		(state: RootState) => state.backtest
	);

	const [addRunOpen, setAddRunOpen] = useState(false);

	useEffect(() => {
		if (!id) return;
		dispatch(fetchBacktestRequest(backtestId));
		dispatch(fetchRunsRequest(backtestId));
	}, [id, dispatch]);

	const handleCloneRun = async (runId: number) => {
		dispatch(cloneRunRequest({ backtestId, runId }));
	};

	function fmtPct(v: number | null): string {
		return v != null ? `${(v * 100).toFixed(2)}%` : "—";
	}
	function fmtNum(v: number | null): string {
		return v != null ? v.toFixed(2) : "—";
	}

	const columns: ColumnsType<BacktestRunDto> = [
		{
			title: "Name",
			dataIndex: "name",
			key: "name",
			sorter: (a: BacktestRunDto, b: BacktestRunDto) =>
				(a.name ?? "").localeCompare(b.name ?? ""),
			defaultSortOrder: "ascend" as const,
			render: (v: string | null, run: BacktestRunDto) => (
				<div onClick={(e) => e.stopPropagation()}>
					<EditableInput
						value={v}
						onSave={(name) =>
							dispatch(
								updateRunRequest({ backtestId, runId: run.id, patch: { name } })
							)
						}
					/>
				</div>
			),
			width: 100,
		},
		{
			title: "Period",
			key: "period",
			width: 150,
			render: (_: unknown, run: BacktestRunDto) => (
				<div onClick={(e) => e.stopPropagation()}>
					<EditableDateRange
						start={run.start_date}
						end={run.end_date}
						onSave={(start, end) =>
							dispatch(
								updateRunRequest({
									backtestId,
									runId: run.id,
									patch: { start, end },
								})
							)
						}
					/>
				</div>
			),
		},
		{
			title: "Status",
			dataIndex: "status",
			key: "status",
			width: 100,
			render: (v: BacktestStatus) => {
				const { status, text } = STATUS_BADGE[v] ?? {
					status: "default",
					text: v,
				};
				return <Badge status={status} text={text} />;
			},
		},
		{
			title: "CAGR",
			dataIndex: "cagr",
			key: "cagr",
			width: 80,
			render: (v: number | null) => (
				<span
					style={{
						color: v != null ? (v >= 0 ? "#3f8600" : "#cf1322") : undefined,
					}}
				>
					{fmtPct(v)}
				</span>
			),
		},
		{
			title: "Sharpe",
			dataIndex: "sharpe",
			key: "sharpe",
			width: 80,
			render: fmtNum,
		},
		{
			title: "Vol",
			dataIndex: "volatility",
			key: "volatility",
			width: 80,
			render: fmtPct,
		},
		{
			title: "MaxDD",
			dataIndex: "max_drawdown",
			key: "max_drawdown",
			width: 80,
			render: (v: number | null) => (
				<span style={{ color: v != null ? "#cf1322" : undefined }}>
					{fmtPct(v)}
				</span>
			),
		},
		{
			title: "WinRate",
			dataIndex: "win_rate",
			key: "win_rate",
			width: 85,
			render: fmtPct,
		},
		{
			title: "PF",
			dataIndex: "profit_factor",
			key: "profit_factor",
			width: 70,
			render: fmtNum,
		},
		{
			title: "Trades",
			dataIndex: "n_trades",
			key: "n_trades",
			width: 70,
			render: (v: number | null) => v ?? "—",
		},
		{
			title: "",
			key: "actions",
			align: "center",
			width: 110,
			render: (_: unknown, run: BacktestRunDto) => (
				<div
					onClick={(e) => e.stopPropagation()}
					className="flex justify-center gap-1"
				>
					<Tooltip title="View">
						<Button
							type="text"
							icon={<EyeOutlined />}
							onClick={() =>
								navigate(`/analysis/backtest/${backtestId}/runs/${run.id}`)
							}
						/>
					</Tooltip>
					<Tooltip title="Clone">
						<Button
							type="text"
							icon={<CopyOutlined />}
							onClick={() => handleCloneRun(run.id)}
						/>
					</Tooltip>
					<Tooltip title="Delete">
						<Popconfirm
							title="Delete this run?"
							okText="Delete"
							cancelText="Cancel"
							okButtonProps={{ danger: true }}
							onConfirm={() =>
								dispatch(deleteRunRequest({ backtestId, runId: run.id }))
							}
						>
							<Button type="text" danger icon={<DeleteOutlined />} />
						</Popconfirm>
					</Tooltip>
				</div>
			),
		},
	];

	return (
		<div className="p-6 flex flex-col gap-6">
			<Button
				icon={<ArrowLeftOutlined />}
				onClick={() => navigate("/analysis/backtest")}
				className="self-start"
			>
				Back
			</Button>

			{currentLoading || !current ? (
				<Skeleton active />
			) : (
				<Card
					title={current.name}
					extra={
						<Button
							type="primary"
							icon={<PlusOutlined />}
							size="small"
							onClick={() => setAddRunOpen(true)}
						>
							Add run
						</Button>
					}
				>
					<div className="grid grid-cols-4 gap-x-8 gap-y-3 text-sm mb-6">
						<div>
							<span className="text-gray-500">Frequency</span>
							<p className="font-medium mt-0.5">{current.frequency}</p>
						</div>
						<div>
							<span className="text-gray-500">Version</span>
							<p className="font-medium mt-0.5">{current.strategy_version}</p>
						</div>
						<div>
							<span className="text-gray-500">Created</span>
							<p className="font-medium mt-0.5">
								{new Date(current.created_at).toLocaleDateString("it-IT")}
							</p>
						</div>
						{(current.frequency === FrequencyType.EOD ||
							current.frequency === FrequencyType.EOW) && (
							<div>
								<span className="text-gray-500">Instrument</span>
								<p className="font-medium mt-0.5">
									{capitalize(current.instrument)}
								</p>
							</div>
						)}
						{current.description && (
							<div className="col-span-4">
								<span className="text-gray-500">Description</span>
								<p className="font-medium mt-0.5">{current.description}</p>
							</div>
						)}
					</div>

					<Table
						rowKey="id"
						size="small"
						columns={columns}
						dataSource={runs}
						loading={runsLoading}
						pagination={false}
						scroll={{ x: "max-content" }}
						onRow={(run) => ({
							onClick: () =>
								navigate(`/analysis/backtest/${backtestId}/runs/${run.id}`),
							className: "cursor-pointer",
						})}
					/>
				</Card>
			)}

			{/* Add run modal */}
			<AddBacktestRunModal
				backtestId={backtestId}
				addRunOpen={addRunOpen}
				setAddRunOpen={setAddRunOpen}
			/>
		</div>
	);
}
