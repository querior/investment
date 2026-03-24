import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, Skeleton, Statistic, Table } from "antd";
import { ArrowDownOutlined, ArrowLeftOutlined, ArrowUpOutlined, BorderOutlined, PlayCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
	fetchRunDetailRequest,
	fetchRunWeightsRequest,
	executeRunRequest,
	stopRunRequest,
} from "../features/backtest/reducer";
import type { RootState } from "../store/reducers";
import Chart from "../components/charts/Chart";
import type { AllocationConfig, BacktestStatus, RunWeightDto } from "../services/backtest-service";
import { getAllocationConfigApi, getRunNavApi } from "../services/backtest-service";

const NEUTRAL_PORTFOLIO = [
	{ asset: "Equity",      proxy: "SPY", neutral: "50%", max: "70%" },
	{ asset: "Bond",        proxy: "IEF", neutral: "30%", max: "55%" },
	{ asset: "Commodities", proxy: "DBC", neutral: "10%", max: "30%" },
	{ asset: "Cash",        proxy: "BIL", neutral: "10%", max: "30%" },
];

const STATUS_BADGE: Record<BacktestStatus, { status: "default" | "processing" | "error" | "success" | "warning"; text: string }> = {
	READY:   { status: "default",    text: "Ready" },
	RUNNING: { status: "processing", text: "Running" },
	DONE:    { status: "success",    text: "Done" },
	ERROR:   { status: "error",      text: "Error" },
	STOPPED: { status: "warning",    text: "Stopped" },
};

const ASSETS = ["Equity", "Bond", "Commodities", "Cash"] as const;
type AssetName = typeof ASSETS[number];

type PivotRow = {
	date: string;
	macro_score: number | null;
	pillar_scores: Record<string, number> | null;
} & Record<AssetName, number | undefined>;

function pivotWeights(weights: RunWeightDto[]): PivotRow[] {
	const byDate = new Map<string, PivotRow>();
	for (const w of weights) {
		if (!byDate.has(w.date)) {
			byDate.set(w.date, {
				date: w.date,
				macro_score: w.macro_score,
				pillar_scores: w.pillar_scores ? JSON.parse(w.pillar_scores) : null,
			} as PivotRow);
		}
		const row = byDate.get(w.date)!;
		(row as any)[w.asset] = w.weight;
	}
	return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function WeightCell({ value, prev }: { value: number | undefined; prev: number | undefined }) {
	if (value == null) return <span className="text-gray-400">—</span>;
	const pct = `${(value * 100).toFixed(1)}%`;
	if (prev == null) return <span>{pct}</span>;
	const delta = value - prev;
	const absDelta = `${(Math.abs(delta) * 100).toFixed(1)}%`;
	if (Math.abs(delta) < 0.0001) return <span>{pct} <span className="text-gray-400 text-xs">(=)</span></span>;
	return (
		<span>
			{pct}{" "}
			<span className={`text-xs ${delta > 0 ? "text-green-600" : "text-red-500"}`}>
				({delta > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {absDelta})
			</span>
		</span>
	);
}

function MacroScoreCell({ row }: { row: PivotRow }) {
	if (row.macro_score == null) return <span className="text-gray-400">—</span>;
	const pillars = row.pillar_scores
		? Object.entries(row.pillar_scores).map(([k, v]) => `${k[0]}=${v > 0 ? "+" : ""}${v.toFixed(2)}`).join(" ")
		: null;
	return (
		<span>
			<span className={row.macro_score >= 0 ? "text-green-600" : "text-red-500"}>
				{row.macro_score > 0 ? "+" : ""}{row.macro_score.toFixed(3)}
			</span>
			{pillars && <span className="text-gray-400 text-xs ml-1">({pillars})</span>}
		</span>
	);
}

function buildAllocationColumns(rows: PivotRow[]): ColumnsType<PivotRow> {
	return [
		{ title: "Date", dataIndex: "date", key: "date", width: 110 },
		{
			title: "MacroScore",
			key: "macro_score",
			render: (_: unknown, row: PivotRow) => <MacroScoreCell row={row} />,
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

function AllocationMatrixCard({ cfg }: { cfg: AllocationConfig }) {

	const assets = Object.keys(cfg.neutral);
	const pillars = Object.keys(cfg.sensitivity);

	return (
		<Card size="small" title="Allocation matrix">
			<div className="flex gap-8 text-xs mb-4">
				<div>
					<span className="text-gray-500 uppercase tracking-wide text-xs">Scale K</span>
					<p className="font-mono font-medium">{(cfg.scale_k * 100).toFixed(1)}%</p>
				</div>
				<div>
					<span className="text-gray-500 uppercase tracking-wide text-xs">Max |Δ|</span>
					<p className="font-mono font-medium">±{(cfg.max_abs_delta * 100).toFixed(0)}%</p>
				</div>
				<div>
					<span className="text-gray-500 uppercase tracking-wide text-xs">MacroScore weights</span>
					<p className="font-mono font-medium">
						{pillars.map((p) => `${p[0]}=${cfg.macro_score_weights[p] ?? 0 > 0 ? "+" : ""}${(cfg.macro_score_weights[p] ?? 0).toFixed(2)}`).join("  ")}
					</p>
				</div>
			</div>

			<table className="text-xs w-full border-collapse">
				<thead>
					<tr>
						<th className="text-left text-gray-500 font-normal pb-1 pr-4">Pillar</th>
						{assets.map((a) => (
							<th key={a} className="text-right text-gray-500 font-normal pb-1 px-3">{a}</th>
						))}
					</tr>
				</thead>
				<tbody>
					{pillars.map((p) => (
						<tr key={p} className="border-t border-gray-100">
							<td className="py-1 pr-4 font-medium">{p}</td>
							{assets.map((a) => {
								const v = cfg.sensitivity[p]?.[a] ?? 0;
								return (
									<td key={a} className={`py-1 px-3 text-right font-mono ${v > 0 ? "text-green-600" : v < 0 ? "text-red-500" : "text-gray-400"}`}>
										{v > 0 ? "+" : ""}{v.toFixed(2)}
									</td>
								);
							})}
						</tr>
					))}
					<tr className="border-t border-gray-300">
						<td className="py-1 pr-4 text-gray-500">Neutral</td>
						{assets.map((a) => (
							<td key={a} className="py-1 px-3 text-right font-mono text-gray-700">
								{((cfg.neutral[a] ?? 0) * 100).toFixed(0)}%
							</td>
						))}
					</tr>
				</tbody>
			</table>
		</Card>
	);
}

function fmt(v: number | null | undefined, percent = false, decimals = 2): string {
	if (v == null) return "—";
	return percent ? `${(v * 100).toFixed(decimals)}%` : v.toFixed(decimals);
}

export default function BacktestRunDetail() {
	const { id, runId } = useParams<{ id: string; runId: string }>();
	const backtestId = Number(id);
	const runIdNum = Number(runId);
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { currentRun, currentRunLoading, runWeights, runWeightsLoading, executingRunId } = useSelector(
		(state: RootState) => state.backtest
	);

	const isExecuting = executingRunId === runIdNum;
	const [allocationConfig, setAllocationConfig] = useState<AllocationConfig | null>(null);
	const [navData, setNavData] = useState<{ date: string; nav: number }[]>([]);

	useEffect(() => {
		dispatch(fetchRunDetailRequest({ backtestId, runId: runIdNum }));
		dispatch(fetchRunWeightsRequest({ backtestId, runId: runIdNum }));
		getAllocationConfigApi().then(setAllocationConfig).catch(() => {});
	}, [backtestId, runIdNum, dispatch]);

	// Aggiorna il grafico NAV ogni volta che il run viene aggiornato (polling o caricamento iniziale)
	useEffect(() => {
		if (!currentRun) return;
		getRunNavApi(backtestId, runIdNum).then(setNavData).catch(() => {});
	}, [currentRun?.updated_at, backtestId, runIdNum]);

	const handleExecute = () => {
		dispatch(executeRunRequest({ backtestId, runId: runIdNum }));
	};

	const handleStop = () => {
		dispatch(stopRunRequest({ backtestId, runId: runIdNum }));
	};

	const isDone = currentRun?.status === "DONE";
	const isRunning = currentRun?.status === "RUNNING" || isExecuting;

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
								<Button type="primary" icon={<PlayCircleOutlined />} onClick={handleExecute}>
									Execute
								</Button>
							)
						}
					>
						<div className="flex items-center gap-8 text-sm">
							<div>
								<span className="text-gray-500 block">Index</span>
								<span className="font-medium">{currentRun.primary_index}</span>
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
							<div>
								<span className="text-gray-500 block">From</span>
								<span className="font-medium">{currentRun.start_date}</span>
							</div>
							<div>
								<span className="text-gray-500 block">To</span>
								<span className="font-medium">{currentRun.end_date}</span>
							</div>
							{currentRun.notes && (
								<div>
									<span className="text-gray-500 block">Notes</span>
									<span className="font-medium">{currentRun.notes}</span>
								</div>
							)}
							{currentRun.status === "ERROR" && currentRun.error_message && (
								<div className="col-span-full mt-1">
									<span className="text-gray-500 block">Error</span>
									<span className="text-red-500 text-xs font-mono">{currentRun.error_message}</span>
								</div>
							)}
						</div>

						<div className="mt-4 pt-4 border-t border-gray-100">
							<span className="text-gray-500 text-xs uppercase tracking-wide">Portafoglio neutro</span>
							<div className="flex gap-6 mt-2">
								{NEUTRAL_PORTFOLIO.map(({ asset, neutral, max, proxy }) => (
									<div key={asset} className="text-sm">
										<span className="font-medium">{asset}</span>
										<span className="text-gray-400 ml-1">({proxy})</span>
										<div className="text-gray-700">{neutral} <span className="text-gray-400 text-xs">max {max}</span></div>
									</div>
								))}
							</div>
						</div>
					</Card>

					{/* Metrics */}
					<div className="grid grid-cols-4 gap-4">
							<Card size="small">
								<Statistic
									title="CAGR"
									value={fmt(currentRun.cagr, true)}
									valueStyle={{ color: (currentRun.cagr ?? 0) >= 0 ? "#3f8600" : "#cf1322" }}
								/>
							</Card>
							<Card size="small">
								<Statistic title="Sharpe Ratio" value={fmt(currentRun.sharpe)} />
							</Card>
							<Card size="small">
								<Statistic title="Volatility" value={fmt(currentRun.volatility, true)} />
							</Card>
							<Card size="small">
								<Statistic
									title="Max Drawdown"
									value={fmt(currentRun.max_drawdown, true)}
									valueStyle={{ color: "#cf1322" }}
								/>
							</Card>
							<Card size="small">
								<Statistic title="Win Rate" value={fmt(currentRun.win_rate, true)} />
							</Card>
							<Card size="small">
								<Statistic title="Profit Factor" value={fmt(currentRun.profit_factor)} />
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
							series={[{
								key: "nav",
								label: "NAV",
								color: "#3b82f6",
								type: "line",
								data: navData.map((d) => ({ date: new Date(d.date), value: d.nav })),
							}]}
						/>
					</Card>
				)}

				{/* Allocation matrix */}
				{(() => {
					const cfg = currentRun.config_snapshot
						? (() => { try { return JSON.parse(currentRun.config_snapshot) as AllocationConfig; } catch { return null; } })()
						: allocationConfig;
					return cfg ? <AllocationMatrixCard cfg={cfg} /> : null;
				})()}

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
									pagination={{ pageSize: 20, showTotal: (t) => `${t} records` }}
									locale={{ emptyText: isDone ? "No allocation data" : "Run the backtest to see allocations" }}
								/>
							);
						})()}
					</Card>
				</>
			)}
		</div>
	);
}
