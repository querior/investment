import { useEffect, useState, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
	Badge,
	Button,
	Card,
	DatePicker,
	Input,
	Popconfirm,
	Skeleton,
} from "antd";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import {
	ArrowLeftOutlined,
	BorderOutlined,
	CheckOutlined,
	CloseOutlined,
	EditOutlined,
	FileTextOutlined,
	PlayCircleOutlined,
	ReloadOutlined,
} from "@ant-design/icons";
import {
	fetchRunDetailRequest,
	fetchRunStatusRequest,
	fetchRunWeightsRequest,
	fetchBacktestConfigRequest,
	fetchBacktestRequest,
	executeRunRequest,
	stopRunRequest,
	updateRunRequest,
	invalidateRunRequest,
	fetchPortfolioPerformanceRequest,
} from "../../features/backtest/reducer";
import type { RootState } from "../../store/reducers";
import Chart from "../../components/charts/Chart";

import { BacktestStatus, FrequencyType } from "../../features/backtest/types";
import { capitalize } from "../../utils/string";
import RegimeAdjustmentsCard from "./Long/RegimeAdjustmentCard";
import Metrics from "./Metrics";
import PerformanceTable from "./PerformanceTable";
import AllocationTable from "./Long/AllocationTable";
import PositionsTable from "./Short/PortfolioPerformanceTable";
import ParameterEditor from "../../components/backtest/ParameterEditor";

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

export default function BacktestRunDetail() {
	const { id, runId } = useParams<{ id: string; runId: string }>();
	const backtestId = Number(id);
	const runIdNum = Number(runId);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const {
		current: currentBacktest,
		currentRun,
		invalidatingRunId,
		backtestConfig,
	} = useSelector((state: RootState) => state.backtest);

	// NAV data from currentRun instead of separate navData state
	const navData = currentRun?.nav || [];

	const isRunning = currentRun?.status === "RUNNING";

	// Polling for portfolio performance during execution
	const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
		null
	);

	const refreshData = () => {
		dispatch(
			fetchRunDetailRequest({
				backtestId,
				runId: runIdNum,
			})
		);
		dispatch(
			fetchPortfolioPerformanceRequest({
				backtestId,
				runId: runIdNum,
			})
		);
	};

	const pollData = () => {
		dispatch(
			fetchRunStatusRequest({
				backtestId,
				runId: runIdNum,
			})
		);
		dispatch(
			fetchPortfolioPerformanceRequest({
				backtestId,
				runId: runIdNum,
			})
		);
	};

	const handleExecute = () => {
		dispatch(executeRunRequest({ backtestId, runId: runIdNum }));
	};

	const handleStop = () => {
		dispatch(stopRunRequest({ backtestId, runId: runIdNum }));
	};

	const [isEditingParams, setIsEditingParams] = useState(false);

	const handleSaveParams = (parameters: Record<string, string>) => {
		dispatch(
			updateRunRequest({
				backtestId,
				runId: runIdNum,
				patch: { parameters },
			})
		);
		dispatch(invalidateRunRequest({ backtestId, runId: runIdNum }));
		setIsEditingParams(false);
	};

	const handleCancelParams = () => {
		setIsEditingParams(false);
	};

	type InfoDraft = { name: string; start: string; end: string };
	const [isEditingInfo, setIsEditingInfo] = useState(false);
	const [infoDraft, setInfoDraft] = useState<InfoDraft | null>(null);

	const startEditInfo = () => {
		if (!currentRun) return;
		setInfoDraft({
			name: currentRun.name ?? "",
			start: currentRun.start_date,
			end: currentRun.end_date,
		});
		setIsEditingInfo(true);
	};

	const cancelEditInfo = () => {
		setIsEditingInfo(false);
		setInfoDraft(null);
	};

	const saveInfo = () => {
		if (!infoDraft) return;
		dispatch(
			updateRunRequest({
				backtestId,
				runId: runIdNum,
				patch: {
					name: infoDraft.name || undefined,
					start: infoDraft.start,
					end: infoDraft.end,
				},
			})
		);
		setIsEditingInfo(false);
		setInfoDraft(null);
	};

	useEffect(() => {
		dispatch(fetchBacktestRequest(backtestId));

		if (currentBacktest?.frequency === FrequencyType.EOM) {
			dispatch(fetchRunWeightsRequest({ backtestId, runId: runIdNum }));
		}

		// Carica parameter schema per tutti i tipi di backtest
		dispatch(fetchBacktestConfigRequest(backtestId));
	}, [backtestId, runIdNum, dispatch, isRunning]);

	useEffect(() => {
		if (
			!currentRun ||
			currentRun.status !== "RUNNING" ||
			currentBacktest?.frequency !== FrequencyType.EOD
		) {
			if (pollingIntervalRef.current) {
				clearInterval(pollingIntervalRef.current);
				pollingIntervalRef.current = null;
			}
			return;
		}

		if (!pollingIntervalRef.current)
			pollingIntervalRef.current = setInterval(pollData, 5000);

		return () => {
			if (pollingIntervalRef.current) {
				clearInterval(pollingIntervalRef.current);
				pollingIntervalRef.current = null;
			}
		};
	}, [currentRun?.status, currentBacktest?.frequency, runIdNum, backtestId]);

	useEffect(refreshData, []);

	if (!currentRun) return <Skeleton active />;

	return (
		<div className="p-6 flex flex-col gap-6">
			<Button
				icon={<ArrowLeftOutlined />}
				onClick={() => navigate(`/analysis/backtest/${id}`)}
				className="self-start"
			>
				Back
			</Button>

			{/* Info + execute */}
			<Card
				size="small"
				extra={
					isRunning ? (
						<Button danger icon={<BorderOutlined />} onClick={handleStop}>
							Stop
						</Button>
					) : (
						<div className="flex gap-2">
							{(currentRun.status === "DONE" ||
								currentRun.status === "ERROR" ||
								currentRun.status === "STOPPED") && (
								<Popconfirm
									title="Cancella i risultati e riporta il run a READY?"
									okText="Reset"
									okButtonProps={{ danger: true }}
									cancelText="Annulla"
									onConfirm={() =>
										dispatch(
											invalidateRunRequest({ backtestId, runId: runIdNum })
										)
									}
								>
									<Button
										icon={<ReloadOutlined />}
										loading={invalidatingRunId === runIdNum}
									>
										Reset
									</Button>
								</Popconfirm>
							)}
							<Button
								type="primary"
								icon={<PlayCircleOutlined />}
								onClick={handleExecute}
							>
								Execute
							</Button>
						</div>
					)
				}
			>
				<div className="flex gap-0">
					{/* LEFT — meta + portafoglio neutro */}
					<div className="w-1/2 pr-6 flex flex-col gap-4">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-2">
								<FileTextOutlined className="text-gray-500" />
								<span className="text-gray-500 text-xs uppercase tracking-wide">
									Info
								</span>
							</div>
							{!isRunning && (
								<div className="flex gap-2">
									{isEditingInfo ? (
										<>
											<Button
												size="small"
												icon={<CloseOutlined />}
												onClick={cancelEditInfo}
											>
												Annulla
											</Button>
											<Button
												size="small"
												type="primary"
												icon={<CheckOutlined />}
												onClick={saveInfo}
											>
												Salva
											</Button>
										</>
									) : (
										<Button
											size="small"
											icon={<EditOutlined />}
											onClick={startEditInfo}
										>
											Modifica
										</Button>
									)}
								</div>
							)}
						</div>
						<div className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
							<div className="w-full">
								<span className="text-gray-500 block">Name</span>
								{isEditingInfo && infoDraft ? (
									<Input
										size="small"
										value={infoDraft.name}
										onChange={(e) =>
											setInfoDraft({ ...infoDraft, name: e.target.value })
										}
										placeholder="(optional)"
									/>
								) : (
									<span className="font-medium">
										{currentRun.name ?? (
											<span className="text-gray-400">—</span>
										)}
									</span>
								)}
							</div>
							<div>
								<span className="text-gray-500 block">Frequency</span>
								<span className="font-medium">{currentRun.frequency}</span>
							</div>
							<div>
								<span className="text-gray-500 block">Status</span>
								<Badge
									status={STATUS_BADGE[currentRun.status].status}
									text={STATUS_BADGE[currentRun.status].text}
								/>
							</div>
							{isEditingInfo && infoDraft ? (
								<div className="w-full">
									<span className="text-gray-500 block">Period</span>
									<DatePicker.RangePicker
										picker="month"
										size="small"
										format="YYYY-MM"
										value={
											[dayjs(infoDraft.start), dayjs(infoDraft.end)] as [
												Dayjs,
												Dayjs
											]
										}
										onChange={(_dates, strs) => {
											if (strs[0] && strs[1]) {
												setInfoDraft({
													...infoDraft,
													start: strs[0] + "-01",
													end: strs[1] + "-01",
												});
											}
										}}
									/>
								</div>
							) : (
								<>
									<div>
										<span className="text-gray-500 block">From</span>
										<span className="font-medium">
											{currentRun.start_date.slice(0, 7)}
										</span>
									</div>
									<div>
										<span className="text-gray-500 block">To</span>
										<span className="font-medium">
											{currentRun.end_date.slice(0, 7)}
										</span>
									</div>
								</>
							)}
							{currentBacktest?.instrument && (
								<div className="w-full">
									<span className="text-gray-500 block">Instrument</span>
									<span className="font-medium">
										{capitalize(currentBacktest.instrument)}
									</span>
								</div>
							)}
							{currentRun.notes && (
								<div>
									<span className="text-gray-500 block">Notes</span>
									<span className="font-medium">{currentRun.notes}</span>
								</div>
							)}
							{currentRun.status === "ERROR" && currentRun.error_message && (
								<div className="w-full">
									<span className="text-gray-500 block">Error</span>
									<span className="text-red-500 text-xs font-mono">
										{currentRun.error_message}
									</span>
								</div>
							)}
						</div>
						{currentRun && (
							<PerformanceTable performances={currentRun.performances} />
						)}
					</div>

					{/* DIVIDER */}
					<div className="w-px bg-gray-100 shrink-0 mx-0" />

					{/* RIGHT — Parameter Editor (always visible with tabs) */}
					<div className="w-1/2">
						{currentRun && (
							<ParameterEditor
								currentRun={currentRun}
								backtestConfig={backtestConfig}
								onSave={handleSaveParams}
								onCancel={handleCancelParams}
								onEdit={() => setIsEditingParams(true)}
								loading={invalidatingRunId === runIdNum}
								readOnly={!isEditingParams || isRunning}
							/>
						)}
					</div>
				</div>
			</Card>

			{/* Regime adjustments */}
			{currentBacktest?.frequency === "EOM" && backtestConfig?.adjustments && (
				<RegimeAdjustmentsCard
					adjustments={backtestConfig.adjustments}
					neutral={backtestConfig.neutral}
				/>
			)}

			{/* NAV Summary */}

			<Card size="small" style={{ marginBottom: 16 }}>
				<div className="flex justify-between items-center gap-8">
					<div>
						<div className="text-gray-500 text-xs uppercase tracking-wide block mb-1">
							NAV
						</div>
						<div className="text-2xl font-bold">
							{navData.length > 0 ? "$" : ""}
							{navData[navData.length - 1]?.nav.toFixed(2)}
						</div>
					</div>
					<div>
						<div className="text-gray-500 text-xs uppercase tracking-wide block mb-1">
							Total Return
						</div>
						<div
							className={`text-2xl font-bold ${
								navData.length >= 2
									? navData[navData.length - 1].nav / navData[0].nav - 1 >= 0
										? "text-green-600"
										: "text-red-600"
									: "text-gray-400"
							}`}
						>
							{navData.length >= 2
								? (
										(navData[navData.length - 1].nav / navData[0].nav - 1) *
										100
								  ).toFixed(2)
								: "—"}
							%
						</div>
					</div>
				</div>
			</Card>

			{/* Metrics */}
			{currentRun && <Metrics currentRun={currentRun} />}

			{/* NAV chart */}
			<Card size="small" title="NAV">
				<Chart
					height={220}
					showLegend={false}
					yTickFormat={(v) => v.toFixed(2)}
					series={[
						{
							key: "nav",
							label: "NAV",
							color: "#3b82f6",
							type: "line",
							data: navData.map((d) => ({
								date: new Date(d.date),
								value: d.nav,
							})),
						},
					]}
				/>
			</Card>

			{/* Allocation weights table */}
			{currentBacktest?.frequency === "EOM" && <AllocationTable />}

			{/* Portfolio performances table */}
			{currentBacktest?.frequency === "EOD" && <PositionsTable />}
		</div>
	);
}
