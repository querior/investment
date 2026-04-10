import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import {
	Badge,
	Button,
	Card,
	DatePicker,
	Input,
	InputNumber,
	Popconfirm,
	Select,
	Skeleton,
	Statistic,
	Table,
} from "antd";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import {
	ArrowDownOutlined,
	ArrowLeftOutlined,
	ArrowUpOutlined,
	BorderOutlined,
	CheckOutlined,
	CloseOutlined,
	EditOutlined,
	PlayCircleOutlined,
	ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
	fetchRunDetailRequest,
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

import { getRunNavApi } from "../../services/backtest-service";
import {
	BacktestStatus,
	FrequencyType,
	InitialAllocation,
	RunWeightDto,
} from "../../features/backtest/types";
import { capitalize, fmt } from "../../utils/string";
import RegimeAdjustmentsCard from "./Long/RegimeAdjustmentCard";
import StartingAllocation from "./Long/StartingAllocation";
import Metrics from "./Metrics";
import AllocationTable from "./Long/AllocationTable";
import PortfolioPerformanceTable from "./Short/PortfolioPerformanceTable";

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
		currentRunLoading,
		executingRunId,
		invalidatingRunId,
		backtestConfig,
	} = useSelector((state: RootState) => state.backtest);

	const isExecuting = executingRunId === runIdNum;
	const isRunning = currentRun?.status === "RUNNING" || isExecuting;
	const [navData, setNavData] = useState<{ date: string; nav: number }[]>([]);

	useEffect(() => {
		dispatch(fetchBacktestRequest(backtestId));
		// Carica il run solo se non è in esecuzione (il polling lo aggiorna continuamente se in RUNNING)
		if (!isRunning) {
			dispatch(fetchRunDetailRequest({ backtestId, runId: runIdNum }));
		}
		dispatch(fetchBacktestConfigRequest(backtestId));
	}, [backtestId, runIdNum, dispatch, isRunning]);

	useEffect(() => {
		if (!currentRun) return;
		getRunNavApi(backtestId, runIdNum)
			.then(setNavData)
			.catch(() => {});
	}, [currentRun?.updated_at, backtestId, runIdNum]);

	useEffect(() => {
		if (currentBacktest?.frequency === FrequencyType.EOM) {
			dispatch(fetchRunWeightsRequest({ backtestId, runId: runIdNum }));
		}

		if (currentBacktest?.frequency === FrequencyType.EOD) {
			dispatch(
				fetchPortfolioPerformanceRequest({
					backtestId,
					runId: runIdNum,
				})
			);
		}
	}, [currentBacktest, runIdNum, backtestId, dispatch]);

	const handleExecute = () => {
		dispatch(executeRunRequest({ backtestId, runId: runIdNum }));
	};

	const handleStop = () => {
		dispatch(stopRunRequest({ backtestId, runId: runIdNum }));
	};

	const isDone = currentRun?.status === "DONE";

	type ParamDraft = Record<string, string | number>;

	const [isEditing, setIsEditing] = useState(false);
	const [draft, setDraft] = useState<ParamDraft | null>(null);

	const getParamValueString = (param: any): string => {
		if (typeof param === "string") return param;
		if (typeof param === "object" && param?.value) return param.value;
		return "";
	};

	const getParamUnit = (param: any): string => {
		if (typeof param === "object" && param?.unit) return param.unit;
		return "value";
	};

	const isPercentParam = (key: string, unit?: string): boolean => {
		return unit === "pct";
	};

	const isSelectParam = (key: string): boolean => {
		return key === "initial_allocation";
	};

	const startEdit = () => {
		if (!currentRun?.parameters) return;
		const newDraft: ParamDraft = {};
		for (const [key, param] of Object.entries(currentRun.parameters)) {
			const valueStr = getParamValueString(param);
			const unit = getParamUnit(param);
			if (isPercentParam(key, unit)) {
				newDraft[key] = parseFloat(valueStr) * 100;
			} else {
				newDraft[key] = valueStr;
			}
		}
		setDraft(newDraft);
		setIsEditing(true);
	};

	const cancelEdit = () => {
		setIsEditing(false);
		setDraft(null);
	};

	const INITIAL_ALLOCATION_OPTIONS: {
		value: InitialAllocation;
		label: string;
	}[] = [
		{ value: "neutral", label: "Neutral weights" },
		{ value: "target", label: "First target" },
	];

	const getParamLabel = (key: string): string => {
		return key
			.split("_")
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(" ");
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

	const saveParams = () => {
		if (!draft) return;
		const params: Record<string, string> = {};
		for (const [key, value] of Object.entries(draft)) {
			if (isPercentParam(key)) {
				params[key] = String((value as number) / 100);
			} else {
				params[key] = String(value);
			}
		}
		dispatch(
			updateRunRequest({
				backtestId,
				runId: runIdNum,
				patch: { parameters: params },
			})
		);
		dispatch(invalidateRunRequest({ backtestId, runId: runIdNum }));
		setIsEditing(false);
		setDraft(null);
	};

	return (
		<div className="p-6 flex flex-col gap-6">
			<Button
				icon={<ArrowLeftOutlined />}
				onClick={() => navigate(`/analysis/backtest/${id}`)}
				className="self-start"
			>
				Back
			</Button>

			{currentRunLoading || !currentRun ? (
				<Skeleton active />
			) : (
				<>
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
									<span className="text-gray-500 text-xs uppercase tracking-wide">
										Info
									</span>
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
									{currentRun.status === "ERROR" &&
										currentRun.error_message && (
											<div className="w-full">
												<span className="text-gray-500 block">Error</span>
												<span className="text-red-500 text-xs font-mono">
													{currentRun.error_message}
												</span>
											</div>
										)}
								</div>
							</div>

							{/* DIVIDER */}
							<div className="w-px bg-gray-100 shrink-0 mx-0" />

							{/* RIGHT — parametri di esecuzione */}
							<div className="w-1/2 pl-6">
								<div className="flex items-center justify-between mb-3">
									<span className="text-gray-500 text-xs uppercase tracking-wide">
										Execution parameters
									</span>
									{currentRun && !isRunning && (
										<div className="flex gap-2">
											{isEditing ? (
												<>
													<Button
														size="small"
														icon={<CloseOutlined />}
														onClick={cancelEdit}
													>
														Annulla
													</Button>
													<Button
														size="small"
														type="primary"
														icon={<CheckOutlined />}
														onClick={saveParams}
														loading={invalidatingRunId === runIdNum}
													>
														Salva
													</Button>
												</>
											) : (
												<Button
													size="small"
													icon={<EditOutlined />}
													onClick={startEdit}
												>
													Modifica
												</Button>
											)}
										</div>
									)}
								</div>
								<div className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
									{currentRun?.parameters &&
										Object.entries(currentRun.parameters).map(
											([key, param]) => {
												const valueStr = getParamValueString(param);
												const unit = getParamUnit(param);
												const isPercent = isPercentParam(key, unit);
												const isSelect = isSelectParam(key);
												const displayLabel = getParamLabel(key);
												const displayValue = isPercent
													? (parseFloat(valueStr) * 100).toFixed(0) + "%"
													: valueStr;

												return (
													<div
														key={key}
														className={isSelect ? "col-span-2" : ""}
													>
														<span className="text-gray-500 block">
															{displayLabel}
														</span>
														{isEditing && draft ? (
															isSelect ? (
																<Select
																	size="small"
																	className="w-40"
																	value={draft[key] as string}
																	options={INITIAL_ALLOCATION_OPTIONS}
																	onChange={(v) =>
																		setDraft({ ...draft, [key]: v })
																	}
																/>
															) : isPercent ? (
																<span className="flex items-center gap-1">
																	<InputNumber
																		size="small"
																		min={0}
																		max={100}
																		step={5}
																		className="w-20"
																		value={draft[key] as number}
																		onChange={(v) =>
																			v != null &&
																			setDraft({ ...draft, [key]: v })
																		}
																	/>
																	<span className="text-gray-400">%</span>
																</span>
															) : (
																<Input
																	size="small"
																	value={draft[key] as string}
																	onChange={(e) =>
																		setDraft({
																			...draft,
																			[key]: e.target.value,
																		})
																	}
																/>
															)
														) : (
															<span className="font-mono font-medium">
																{displayValue}
															</span>
														)}
													</div>
												);
											}
										)}

									{currentBacktest?.frequency === "EOM" && (
										<StartingAllocation draft={draft} />
									)}
								</div>
							</div>
						</div>
					</Card>

					{/* Regime adjustments */}
					{currentBacktest?.frequency === "EOM" &&
						backtestConfig?.adjustments && (
							<RegimeAdjustmentsCard
								adjustments={backtestConfig.adjustments}
								neutral={backtestConfig.neutral}
							/>
						)}

					{/* Metrics */}
					{currentRun && <Metrics currentRun={currentRun} />}

					{/* NAV chart */}
					{navData.length > 0 && (
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
					)}

					{/* Allocation weights table */}
					{currentBacktest?.frequency === "EOM" && <AllocationTable />}

					{/* Portfolio performances table */}
					{currentBacktest?.frequency === "EOD" && (
						<PortfolioPerformanceTable />
					)}
				</>
			)}
		</div>
	);
}
