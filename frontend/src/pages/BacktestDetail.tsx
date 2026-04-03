import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
	Badge,
	Button,
	Card,
	DatePicker,
	Form,
	Input,
	Modal,
	Popconfirm,
	Select,
	Skeleton,
	Table,
	Tooltip,
} from "antd";
import {
	ArrowLeftOutlined,
	CopyOutlined,
	DeleteOutlined,
	EditOutlined,
	EyeOutlined,
	PlusOutlined,
} from "@ant-design/icons";
import { cloneRunApi } from "../services/backtest-service";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import type { ColumnsType } from "antd/es/table";
import {
	fetchBacktestRequest,
	fetchRunsRequest,
	createRunRequest,
	createRunSuccess,
	updateRunRequest,
	deleteRunRequest,
} from "../features/backtest/reducer";
import type { RootState } from "../store/reducers";
import type {
	BacktestRunDto,
	BacktestStatus,
	InitialAllocation,
} from "../services/backtest-service";

const STATUS_BADGE: Record<
	BacktestStatus,
	{
		status: "default" | "processing" | "error" | "success" | "warning";
		text: string;
	}
> = {
	READY: { status: "default", text: "Ready" },
	RUNNING: { status: "processing", text: "Running" },
	DONE: { status: "success", text: "Done" },
	ERROR: { status: "error", text: "Error" },
	STOPPED: { status: "warning", text: "Stopped" },
};

const INITIAL_ALLOCATION_OPTIONS: { value: InitialAllocation; label: string }[] = [
	{ value: "neutral", label: "Neutral weights" },
	{ value: "target",  label: "First target" },
];

type AddRunFormValues = {
	name?: string;
	range: [Dayjs, Dayjs];
	notes?: string;
	initial_allocation: InitialAllocation;
};

function EditableRunName({
	value,
	onSave,
}: {
	value: string | null;
	onSave: (v: string) => void;
}) {
	const [editing, setEditing] = useState(false);
	const [val, setVal] = useState(value ?? "");
	const inputRef = useRef<HTMLInputElement>(null);

	const startEdit = (e: React.MouseEvent) => {
		e.stopPropagation();
		setVal(value ?? "");
		setEditing(true);
		setTimeout(() => inputRef.current?.focus(), 0);
	};

	const commit = () => {
		setEditing(false);
		onSave(val);
	};

	if (editing) {
		return (
			<input
				ref={inputRef}
				value={val}
				onChange={(e) => setVal(e.target.value)}
				onBlur={commit}
				onKeyDown={(e) => {
					if (e.key === "Enter") commit();
					if (e.key === "Escape") setEditing(false);
				}}
				onClick={(e) => e.stopPropagation()}
				className="border border-blue-400 rounded px-1 text-sm w-full outline-none"
			/>
		);
	}

	return (
		<div className="flex items-center justify-between gap-2 min-w-0">
			<span className="truncate text-sm">
				{value ?? <span className="text-gray-400">—</span>}
			</span>
			<Button
				type="text"
				size="small"
				icon={<EditOutlined />}
				onClick={startEdit}
				className="shrink-0"
			/>
		</div>
	);
}

function EditableDateRange({
	start,
	end,
	onSave,
}: {
	start: string;
	end: string;
	onSave: (start: string, end: string) => void;
}) {
	const [editing, setEditing] = useState(false);

	const startEdit = (e: React.MouseEvent) => {
		e.stopPropagation();
		setEditing(true);
	};

	if (editing) {
		return (
			<DatePicker.RangePicker
				picker="month"
				size="small"
				format="YYYY-MM"
				defaultValue={[dayjs(start), dayjs(end)] as [Dayjs, Dayjs]}
				autoFocus
				open
				onChange={(dates, strs) => {
					if (dates && strs[0] && strs[1])
						onSave(strs[0] + "-01", strs[1] + "-01");
					setEditing(false);
				}}
				onOpenChange={(open) => {
					if (!open) setEditing(false);
				}}
				onClick={(e) => e.stopPropagation()}
			/>
		);
	}

	return (
		<div className="flex items-center justify-between gap-2">
			<span className="text-sm">
				{start.slice(0, 7)} → {end.slice(0, 7)}
			</span>
			<Button
				type="text"
				size="small"
				icon={<EditOutlined />}
				onClick={startEdit}
				className="shrink-0"
			/>
		</div>
	);
}

export default function BacktestDetail() {
	const { id } = useParams<{ id: string }>();
	const backtestId = Number(id);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { current, currentLoading, runs, runsLoading, creatingRun } =
		useSelector((state: RootState) => state.backtest);

	const [addRunOpen, setAddRunOpen] = useState(false);
	const [addRunForm] = Form.useForm<AddRunFormValues>();

	useEffect(() => {
		if (!id) return;
		dispatch(fetchBacktestRequest(backtestId));
		dispatch(fetchRunsRequest(backtestId));
	}, [id, dispatch]);

	const handleAddRun = async () => {
		const values = await addRunForm.validateFields();
		dispatch(
			createRunRequest({
				backtestId,
				payload: {
					name: values.name || undefined,
					start: values.range[0].format("YYYY-MM-DD"),
					end: values.range[1].format("YYYY-MM-DD"),
					notes: values.notes,
					initial_allocation: values.initial_allocation,
				},
			})
		);
		setAddRunOpen(false);
		addRunForm.resetFields();
	};

	const handleCloneRun = async (runId: number) => {
		const cloned = await cloneRunApi(backtestId, runId);
		dispatch(createRunSuccess(cloned));
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
			sorter: (a: BacktestRunDto, b: BacktestRunDto) => (a.name ?? "").localeCompare(b.name ?? ""),
			defaultSortOrder: "ascend" as const,
			render: (v: string | null, run: BacktestRunDto) => (
				<div onClick={(e) => e.stopPropagation()}>
					<EditableRunName
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
			<Modal
				title="New run"
				open={addRunOpen}
				onOk={handleAddRun}
				onCancel={() => {
					setAddRunOpen(false);
					addRunForm.resetFields();
				}}
				okText="Create"
				cancelText="Cancel"
				confirmLoading={creatingRun}
				destroyOnHidden
			>
				<Form
					form={addRunForm}
					layout="vertical"
					className="mt-4"
					initialValues={{ initial_allocation: "neutral" }}
				>
					<Form.Item name="name" label="Name">
						<Input placeholder="e.g. M0 baseline" />
					</Form.Item>
					<Form.Item
						name="range"
						label="Period"
						rules={[{ required: true, message: "Select a period" }]}
					>
						<DatePicker.RangePicker
							picker="month"
							style={{ width: "100%" }}
							format="YYYY-MM"
						/>
					</Form.Item>
					<Form.Item
						name="initial_allocation"
						label="Starting allocation"
						rules={[{ required: true }]}
					>
						<Select options={INITIAL_ALLOCATION_OPTIONS} />
					</Form.Item>
					<Form.Item name="notes" label="Notes">
						<Input.TextArea rows={2} placeholder="(optional)" />
					</Form.Item>
				</Form>
			</Modal>
		</div>
	);
}
