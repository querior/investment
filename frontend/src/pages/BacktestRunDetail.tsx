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
	Tabs,
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
	executeRunRequest,
	stopRunRequest,
	updateRunRequest,
	invalidateRunRequest,
} from "../features/backtest/reducer";
import type { RootState } from "../store/reducers";
import Chart from "../components/charts/Chart";
import type {
	AdjustmentDto,
	BacktestStatus,
	InitialAllocation,
	RunWeightDto,
} from "../services/backtest-service";
import { getRunNavApi } from "../services/backtest-service";


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

const REGIME_COLOR: Record<string, string> = {
	expansion: "text-green-600",
	contraction: "text-red-500",
	neutral: "text-gray-400",
};

const ASSETS = ["Equity", "Bond", "Commodities", "Cash"] as const;
type AssetName = (typeof ASSETS)[number];

type PivotRow = {
	date: string;
	pillar_scores: Record<string, string | number> | null; // pillar → regime (new) or score float (old)
} & Record<AssetName, number | undefined>;

function pivotWeights(weights: RunWeightDto[]): PivotRow[] {
	const byDate = new Map<string, PivotRow>();
	for (const w of weights) {
		if (!byDate.has(w.date)) {
			byDate.set(w.date, {
				date: w.date,
				pillar_scores: w.pillar_scores ? JSON.parse(w.pillar_scores) : null,
			} as PivotRow);
		}
		const row = byDate.get(w.date)!;
		(row as any)[w.asset] = w.weight;
	}
	return Array.from(byDate.values()).sort((a, b) =>
		a.date.localeCompare(b.date)
	);
}

function WeightCell({
	value,
	prev,
}: {
	value: number | undefined;
	prev: number | undefined;
}) {
	if (value == null) return <span className="text-gray-400">—</span>;
	const pct = `${(value * 100).toFixed(1)}%`;
	if (prev == null) return <span>{pct}</span>;
	const delta = value - prev;
	const absDelta = `${(Math.abs(delta) * 100).toFixed(1)}%`;
	if (Math.abs(delta) < 0.0001)
		return (
			<span>
				{pct} <span className="text-gray-400 text-xs">(=)</span>
			</span>
		);
	return (
		<span>
			{pct}{" "}
			<span
				className={`text-xs ${delta > 0 ? "text-green-600" : "text-red-500"}`}
			>
				({delta > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {absDelta})
			</span>
		</span>
	);
}

function RegimesCell({ row }: { row: PivotRow }) {
	if (!row.pillar_scores) return <span className="text-gray-400">—</span>;
	return (
		<span className="text-xs flex flex-wrap gap-x-2">
			{Object.entries(row.pillar_scores).map(([pillar, regime]) => {
				const isStr = typeof regime === "string";
				const label = isStr ? (regime as string).slice(0, 3) : (regime as number).toFixed(2);
				const colorKey = isStr ? (regime as string) : "";
				return (
					<span key={pillar} className={REGIME_COLOR[colorKey] ?? "text-gray-400"}>
						{pillar[0]}={label}
					</span>
				);
			})}
		</span>
	);
}

const PILLARS = ["Growth", "Inflation", "Policy", "Risk"] as const;
const REGIMES = ["expansion", "contraction"] as const;

function RegimeAdjustmentsCard({
	adjustments,
	neutral,
}: {
	adjustments: AdjustmentDto[];
	neutral: Record<string, number>;
}) {
	console.log("adjustments", adjustments);
	const assets = Object.keys(neutral);

	const tabItems = REGIMES.map((regime) => {
		const byPillarAsset: Record<string, Record<string, number>> = {};
		for (const p of PILLARS) {
			byPillarAsset[p] = {};
			for (const a of assets) byPillarAsset[p][a] = 0;
		}
		for (const adj of adjustments) {
			if (adj.regime === regime) {
				if (!byPillarAsset[adj.pillar]) byPillarAsset[adj.pillar] = {};
				byPillarAsset[adj.pillar][adj.asset] = adj.delta;
			}
		}

		const rows = PILLARS.map((p) => ({ pillar: p, ...byPillarAsset[p] }));

		const columns: ColumnsType<(typeof rows)[0]> = [
			{ title: "Pillar", dataIndex: "pillar", key: "pillar", width: 100 },
			...assets.map((asset) => ({
				title: asset,
				key: asset,
				width: 110,
				render: (_: unknown, row: (typeof rows)[0]) => {
					const v: number = (row as any)[asset] ?? 0;
					const color =
						v > 0 ? "text-green-600" : v < 0 ? "text-red-500" : "text-gray-400";
					return (
						<span className={`font-mono text-xs ${color}`}>
							{v !== 0 ? `${v > 0 ? "+" : ""}${(v * 100).toFixed(0)}%` : "—"}
						</span>
					);
				},
			})),
			{
				title: "Σ delta",
				key: "sum",
				width: 80,
				render: (_: unknown, row: (typeof rows)[0]) => {
					const sum = assets.reduce(
						(acc, a) => acc + ((row as any)[a] ?? 0),
						0
					);
					const color =
						Math.abs(sum) < 0.001
							? "text-gray-400"
							: "text-amber-600 font-semibold";
					return (
						<span className={`font-mono text-xs ${color}`}>
							{sum > 0 ? "+" : ""}
							{(sum * 100).toFixed(0)}%
						</span>
					);
				},
			},
		];

		return {
			key: regime,
			label: regime.charAt(0).toUpperCase() + regime.slice(1),
			children: (
				<Table
					rowKey="pillar"
					size="small"
					columns={columns}
					dataSource={rows}
					pagination={false}
				/>
			),
		};
	});

	return (
		<Card size="small" title="Allocation adjustments by regime">
			<Tabs size="small" items={tabItems} />
		</Card>
	);
}

function buildAllocationColumns(rows: PivotRow[]): ColumnsType<PivotRow> {
	return [
		{ title: "Date", dataIndex: "date", key: "date", width: 110 },
		{
			title: "Regimes",
			key: "pillar_scores",
			width: 160,
			render: (_: unknown, row: PivotRow) => <RegimesCell row={row} />,
		},
		...ASSETS.map((asset) => ({
			title: asset,
			key: asset,
			render: (_: unknown, row: PivotRow) => {
				const idx = rows.indexOf(row);
				const prev = idx > 0 ? rows[idx - 1][asset] : undefined;
				return <WeightCell value={row[asset]} prev={prev} />;
			},
		})),
	];
}

function fmt(
	v: number | null | undefined,
	percent = false,
	decimals = 2
): string {
	if (v == null) return "—";
	return percent ? `${(v * 100).toFixed(decimals)}%` : v.toFixed(decimals);
}

export default function BacktestRunDetail() {
	const { id, runId } = useParams<{ id: string; runId: string }>();
	const backtestId = Number(id);
	const runIdNum = Number(runId);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const {
		currentRun,
		currentRunLoading,
		runWeights,
		runWeightsLoading,
		executingRunId,
		invalidatingRunId,
		backtestConfig,
	} = useSelector((state: RootState) => state.backtest);

	const isExecuting = executingRunId === runIdNum;
	const [navData, setNavData] = useState<{ date: string; nav: number }[]>([]);

	useEffect(() => {
		dispatch(fetchRunDetailRequest({ backtestId, runId: runIdNum }));
		dispatch(fetchRunWeightsRequest({ backtestId, runId: runIdNum }));
		dispatch(fetchBacktestConfigRequest(backtestId));
	}, [backtestId, runIdNum, dispatch]);

	useEffect(() => {
		if (!currentRun) return;
		getRunNavApi(backtestId, runIdNum)
			.then(setNavData)
			.catch(() => {});
	}, [currentRun?.updated_at, backtestId, runIdNum]);

	const handleExecute = () => {
		dispatch(executeRunRequest({ backtestId, runId: runIdNum }));
	};

	const handleStop = () => {
		dispatch(stopRunRequest({ backtestId, runId: runIdNum }));
	};

	const isDone = currentRun?.status === "DONE";
	const isRunning = currentRun?.status === "RUNNING" || isExecuting;

	const runParam = (key: string, fallback: number): number => {
		const raw = currentRun?.parameters?.[key];
		return raw != null ? parseFloat(raw) : fallback;
	};
	const currentInitialAllocation = (currentRun?.parameters?.["initial_allocation"] ?? "neutral") as InitialAllocation;

	type ParamDraft = {
		coherence_factor: number;
		allocation_alpha: number;
		initial_allocation: InitialAllocation;
	};

	const [isEditing, setIsEditing] = useState(false);
	const [draft, setDraft] = useState<ParamDraft | null>(null);

	const startEdit = () => {
		if (!currentRun) return;
		setDraft({
			coherence_factor: runParam("coherence.factor", 0.5) * 100,
			allocation_alpha: runParam("allocation.alpha", 0.3) * 100,
			initial_allocation: currentInitialAllocation,
		});
		setIsEditing(true);
	};

	const cancelEdit = () => {
		setIsEditing(false);
		setDraft(null);
	};

	const INITIAL_ALLOCATION_OPTIONS: { value: InitialAllocation; label: string }[] = [
		{ value: "neutral", label: "Neutral weights" },
		{ value: "target",  label: "First target" },
	];

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
		dispatch(
			updateRunRequest({
				backtestId,
				runId: runIdNum,
				patch: {
					parameters: {
						"coherence.factor": String(draft.coherence_factor / 100),
						"allocation.alpha": String(draft.allocation_alpha / 100),
						"initial_allocation": draft.initial_allocation,
					},
				},
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
									{(currentRun.status === "DONE" || currentRun.status === "ERROR" || currentRun.status === "STOPPED") && (
										<Popconfirm
											title="Cancella i risultati e riporta il run a READY?"
											okText="Reset"
											okButtonProps={{ danger: true }}
											cancelText="Annulla"
											onConfirm={() => dispatch(invalidateRunRequest({ backtestId, runId: runIdNum }))}
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
									<div>
										<span className="text-gray-500 block">
											Coherence factor
										</span>
										{isEditing && draft ? (
											<span className="flex items-center gap-1">
												<InputNumber
													size="small"
													min={0}
													max={100}
													step={5}
													className="w-20"
													value={draft.coherence_factor}
													onChange={(v) =>
														v != null &&
														setDraft({ ...draft, coherence_factor: v })
													}
												/>
												<span className="text-gray-400">%</span>
											</span>
										) : (
											<span className="font-mono font-medium">
												{(runParam("coherence.factor", 0.5) * 100).toFixed(0)}%
											</span>
										)}
									</div>

									<div>
										<span className="text-gray-500 block">
											Allocation alpha
										</span>
										{isEditing && draft ? (
											<span className="flex items-center gap-1">
												<InputNumber
													size="small"
													min={0}
													max={100}
													step={5}
													className="w-20"
													value={draft.allocation_alpha}
													onChange={(v) =>
														v != null &&
														setDraft({ ...draft, allocation_alpha: v })
													}
												/>
												<span className="text-gray-400">%</span>
											</span>
										) : (
											<span className="font-mono font-medium">
												{(runParam("allocation.alpha", 0.3) * 100).toFixed(0)}%
											</span>
										)}
									</div>

									<div className="col-span-2">
										<span className="text-gray-500 block">Starting allocation</span>
										{isEditing && draft ? (
											<Select
												size="small"
												className="w-40"
												value={draft.initial_allocation}
												options={INITIAL_ALLOCATION_OPTIONS}
												onChange={(v) =>
													setDraft({ ...draft, initial_allocation: v })
												}
											/>
										) : (
											<span className="font-medium">
												{INITIAL_ALLOCATION_OPTIONS.find(
													(o) => o.value === currentInitialAllocation
												)?.label ?? currentInitialAllocation}
											</span>
										)}
									</div>

									{(draft?.initial_allocation ?? currentInitialAllocation) === "neutral" ? (
										backtestConfig && (
											<div className="col-span-2 pt-3 border-t border-gray-100">
												<span className="text-gray-500 text-xs uppercase tracking-wide block mb-2">
													Portafoglio neutro
												</span>
												<div className="flex gap-6">
													{Object.entries(backtestConfig.neutral).map(([asset, w]) => (
														<div key={asset} className="text-sm">
															<span className="font-medium">{asset}</span>
															<div className="font-mono text-gray-700">
																{(w * 100).toFixed(0)}%
															</div>
														</div>
													))}
												</div>
											</div>
										)
									) : (
										<div className="col-span-2 pt-3 border-t border-gray-100">
											<span className="text-gray-400 text-xs">
												L'allocazione iniziale sarà il target calcolato al primo mese disponibile. Visibile dopo l'esecuzione.
											</span>
										</div>
									)}
								</div>
							</div>
						</div>
					</Card>

					{/* Regime adjustments */}
					{backtestConfig && (
						<RegimeAdjustmentsCard
							adjustments={backtestConfig.adjustments}
							neutral={backtestConfig.neutral}
						/>
					)}

					{/* Metrics */}
					<div className="grid grid-cols-4 gap-4">
						<Card size="small">
							<Statistic
								title="CAGR"
								value={fmt(currentRun.cagr, true)}
								valueStyle={{
									color: (currentRun.cagr ?? 0) >= 0 ? "#3f8600" : "#cf1322",
								}}
							/>
						</Card>
						<Card size="small">
							<Statistic title="Sharpe Ratio" value={fmt(currentRun.sharpe)} />
						</Card>
						<Card size="small">
							<Statistic
								title="Volatility"
								value={fmt(currentRun.volatility, true)}
							/>
						</Card>
						<Card size="small">
							<Statistic
								title="Max Drawdown"
								value={fmt(currentRun.max_drawdown, true)}
								valueStyle={{ color: "#cf1322" }}
							/>
						</Card>
						<Card size="small">
							<Statistic
								title="Win Rate"
								value={fmt(currentRun.win_rate, true)}
							/>
						</Card>
						<Card size="small">
							<Statistic
								title="Profit Factor"
								value={fmt(currentRun.profit_factor)}
							/>
						</Card>
						<Card size="small">
							<Statistic title="N. trade" value={currentRun.n_trades ?? "—"} />
						</Card>
					</div>

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
					<Card size="small" title="Allocations">
						{(() => {
							const rows = pivotWeights(runWeights);
							return (
								<Table
									rowKey="date"
									size="small"
									columns={buildAllocationColumns(rows)}
									dataSource={rows}
									loading={runWeightsLoading}
									pagination={{
										pageSize: 20,
										showTotal: (t) => `${t} records`,
									}}
									locale={{
										emptyText: isDone
											? "No allocation data"
											: "Run the backtest to see allocations",
									}}
								/>
							);
						})()}
					</Card>
				</>
			)}
		</div>
	);
}
