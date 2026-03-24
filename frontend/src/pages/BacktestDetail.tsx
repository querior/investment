import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, DatePicker, Form, Input, Modal, Popconfirm, Skeleton, Table, Tooltip } from "antd";
import { ArrowLeftOutlined, DeleteOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import type { Dayjs } from "dayjs";
import type { ColumnsType } from "antd/es/table";
import {
	fetchBacktestRequest,
	fetchRunsRequest,
	createRunRequest,
	deleteRunRequest,
} from "../features/backtest/reducer";
import type { RootState } from "../store/reducers";
import type { BacktestRunDto, BacktestStatus } from "../services/backtest-service";

const STATUS_BADGE: Record<BacktestStatus, { status: "default" | "processing" | "error" | "success" | "warning"; text: string }> = {
	READY:   { status: "default",    text: "Ready" },
	RUNNING: { status: "processing", text: "Running" },
	DONE:    { status: "success",    text: "Done" },
	ERROR:   { status: "error",      text: "Error" },
	STOPPED: { status: "warning",    text: "Stopped" },
};

type AddRunFormValues = {
	range: [Dayjs, Dayjs];
	notes?: string;
};

export default function BacktestDetail() {
	const { id } = useParams<{ id: string }>();
	const backtestId = Number(id);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { current, currentLoading, runs, runsLoading, creatingRun } = useSelector(
		(state: RootState) => state.backtest
	);

	const [addRunOpen, setAddRunOpen] = useState(false);
	const [addRunForm] = Form.useForm<AddRunFormValues>();

	useEffect(() => {
		if (!id) return;
		dispatch(fetchBacktestRequest(backtestId));
		dispatch(fetchRunsRequest(backtestId));
	}, [id, dispatch]);

	const handleAddRun = async () => {
		const values = await addRunForm.validateFields();
		dispatch(createRunRequest({
			backtestId,
			payload: {
				start: values.range[0].format("YYYY-MM-DD"),
				end: values.range[1].format("YYYY-MM-DD"),
				notes: values.notes,
			},
		}));
		setAddRunOpen(false);
		addRunForm.resetFields();
	};

	function fmtPct(v: number | null): string {
		return v != null ? `${(v * 100).toFixed(2)}%` : "—";
	}
	function fmtNum(v: number | null): string {
		return v != null ? v.toFixed(2) : "—";
	}

	const columns: ColumnsType<BacktestRunDto> = [
		{ title: "From", dataIndex: "start_date", key: "start_date", width: 100 },
		{ title: "To", dataIndex: "end_date", key: "end_date", width: 100 },
		{
			title: "Status",
			dataIndex: "status",
			key: "status",
			width: 100,
			render: (v: BacktestStatus) => {
				const { status, text } = STATUS_BADGE[v] ?? { status: "default", text: v };
				return <Badge status={status} text={text} />;
			},
		},
		{
			title: "CAGR",
			dataIndex: "cagr",
			key: "cagr",
			width: 80,
			render: (v: number | null) => (
				<span style={{ color: v != null ? (v >= 0 ? "#3f8600" : "#cf1322") : undefined }}>
					{fmtPct(v)}
				</span>
			),
		},
		{ title: "Sharpe", dataIndex: "sharpe", key: "sharpe", width: 80, render: fmtNum },
		{ title: "Vol", dataIndex: "volatility", key: "volatility", width: 80, render: fmtPct },
		{
			title: "MaxDD",
			dataIndex: "max_drawdown",
			key: "max_drawdown",
			width: 80,
			render: (v: number | null) => (
				<span style={{ color: v != null ? "#cf1322" : undefined }}>{fmtPct(v)}</span>
			),
		},
		{ title: "WinRate", dataIndex: "win_rate", key: "win_rate", width: 85, render: fmtPct },
		{ title: "PF", dataIndex: "profit_factor", key: "profit_factor", width: 70, render: fmtNum },
		{ title: "Trades", dataIndex: "n_trades", key: "n_trades", width: 70, render: (v: number | null) => v ?? "—" },
		{
			title: "",
			key: "actions",
			align: "center",
			width: 80,
			render: (_: unknown, run: BacktestRunDto) => (
				<div onClick={(e) => e.stopPropagation()} className="flex justify-center gap-1">
					<Tooltip title="View">
						<Button
							type="text"
							icon={<EyeOutlined />}
							onClick={() => navigate(`/analysis/backtest/${backtestId}/runs/${run.id}`)}
						/>
					</Tooltip>
					<Tooltip title="Delete">
						<Popconfirm
							title="Delete this run?"
							okText="Delete"
							cancelText="Cancel"
							okButtonProps={{ danger: true }}
							onConfirm={() => dispatch(deleteRunRequest({ backtestId, runId: run.id }))}
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
							<span className="text-gray-500">Primary index</span>
							<p className="font-medium mt-0.5">{current.primary_index}</p>
						</div>
						<div>
							<span className="text-gray-500">Version</span>
							<p className="font-medium mt-0.5">{current.strategy_version}</p>
						</div>
						<div>
							<span className="text-gray-500">Created</span>
							<p className="font-medium mt-0.5">{new Date(current.created_at).toLocaleDateString("it-IT")}</p>
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
							onClick: () => navigate(`/analysis/backtest/${backtestId}/runs/${run.id}`),
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
				onCancel={() => { setAddRunOpen(false); addRunForm.resetFields(); }}
				okText="Create"
				cancelText="Cancel"
				confirmLoading={creatingRun}
				destroyOnHidden
			>
				<Form form={addRunForm} layout="vertical" className="mt-4">
					<Form.Item name="range" label="Period" rules={[{ required: true, message: "Select a period" }]}>
						<DatePicker.RangePicker picker="month" style={{ width: "100%" }} format="YYYY-MM" />
					</Form.Item>
					<Form.Item name="notes" label="Notes">
						<Input.TextArea rows={2} placeholder="(optional)" />
					</Form.Item>
				</Form>
			</Modal>
		</div>
	);
}
