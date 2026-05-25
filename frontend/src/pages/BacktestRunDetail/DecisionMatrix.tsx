import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import { Card, Tag, Spin, Empty, Tooltip, Progress, Collapse } from "antd";
import { fetchDecisionMatrixRequest } from "../../features/backtest/reducer";
import type { RootState } from "../../store/reducers";
import type { DecisionMatrixRow, ZoneStat } from "../../features/backtest/types";
import { getStrategyMeta } from "../../utils/strategy";

const ZONE_META: Record<string, { label: string; description: string; color: string }> = {
	A: { label: "Zone A", description: "Trend + Low IV  (ADX ≥ 25, IV rank < 30)", color: "#1677ff" },
	B: { label: "Zone B", description: "Trend + High IV  (ADX ≥ 25, IV rank ≥ 30)", color: "#fa8c16" },
	C: { label: "Zone C", description: "Lateral + Low IV  (ADX < 25, IV rank < 30)", color: "#52c41a" },
	D: { label: "Zone D", description: "Lateral + High IV  (ADX < 25, IV rank ≥ 30)", color: "#722ed1" },
};

const ACTION_COLOR: Record<string, string> = {
	OPEN: "success",
	MONITOR: "warning",
	SKIP: "error",
};

const SUB_SCORES = [
	{ key: "avg_pricing_edge", label: "Edge (35%)", color: "#1677ff" },
	{ key: "avg_risk_reward", label: "R/R (25%)", color: "#52c41a" },
	{ key: "avg_breakeven", label: "Breakeven (20%)", color: "#fa8c16" },
	{ key: "avg_execution_cost", label: "Exec cost (15%)", color: "#722ed1" },
	{ key: "avg_capital_efficiency", label: "Cap eff (5%)", color: "#eb2f96" },
] as const;

function ScoreBar({ value, color }: { value: number | null; color: string }) {
	if (value == null) return <span className="text-gray-300 text-xs">—</span>;
	return (
		<Tooltip title={`${value.toFixed(1)}/100`}>
			<div className="flex items-center gap-1">
				<Progress percent={value} showInfo={false} strokeColor={color} size={[80, 6]} />
				<span className="text-xs text-gray-500 w-8">{value.toFixed(0)}</span>
			</div>
		</Tooltip>
	);
}

type GroupedRow = {
	strategy_name: string;
	decisions: Record<string, DecisionMatrixRow>;
};

function ZoneContent({ rows }: { rows: DecisionMatrixRow[] }) {
	const byStrategy: Record<string, GroupedRow> = {};
	for (const row of rows) {
		if (!byStrategy[row.strategy_name]) {
			byStrategy[row.strategy_name] = { strategy_name: row.strategy_name, decisions: {} };
		}
		byStrategy[row.strategy_name].decisions[row.decision_action] = row;
	}

	const strategies = Object.values(byStrategy);
	if (strategies.length === 0) return null;

	return (
		<div className="space-y-4">
			{strategies.map((sg) => {
				const stratMeta = getStrategyMeta(sg.strategy_name);
				const actions = ["OPEN", "MONITOR", "SKIP"];
				return (
					<div key={sg.strategy_name} className="border border-gray-100 rounded p-3">
						<div className="flex items-center gap-2 mb-3">
							{stratMeta ? (
								<Tag color={stratMeta.color}>{stratMeta.acronym}</Tag>
							) : (
								<Tag>{sg.strategy_name}</Tag>
							)}
						</div>
						<div className="grid grid-cols-3 gap-3">
							{actions.map((action) => {
								const d = sg.decisions[action];
								if (!d) return (
									<div key={action} className="bg-gray-50 rounded p-2 opacity-40">
										<Tag color={ACTION_COLOR[action]}>{action}</Tag>
										<span className="text-xs text-gray-400 ml-1">0</span>
									</div>
								);
								return (
									<div key={action} className="bg-gray-50 rounded p-2">
										<div className="flex items-center gap-2 mb-2">
											<Tag color={ACTION_COLOR[action]}>{action}</Tag>
											<span className="text-xs font-semibold">{d.count}x</span>
											{d.avg_score != null && (
												<span className="text-xs text-gray-500">
													score: <b>{d.avg_score.toFixed(0)}</b>
												</span>
											)}
										</div>
										<div className="space-y-1">
											{SUB_SCORES.map(({ key, label, color }) => (
												<div key={key} className="flex items-center gap-1">
													<span className="text-xs text-gray-400 w-28 shrink-0">{label}</span>
													<ScoreBar value={d[key as keyof DecisionMatrixRow] as number | null} color={color} />
												</div>
											))}
										</div>
										{(d.avg_iv_rank != null || d.avg_adx != null) && (
											<div className="mt-2 flex gap-3 text-xs text-gray-400">
												{d.avg_iv_rank != null && <span>IV rank: {d.avg_iv_rank.toFixed(1)}</span>}
												{d.avg_adx != null && <span>ADX: {d.avg_adx.toFixed(1)}</span>}
												{d.avg_entry_score != null && <span>Entry: {d.avg_entry_score.toFixed(0)}</span>}
											</div>
										)}
									</div>
								);
							})}
						</div>
					</div>
				);
			})}
		</div>
	);
}

const DecisionMatrix: React.FC = () => {
	const { id, runId } = useParams<{ id: string; runId: string }>();
	const backtestId = Number(id);
	const runIdNum = Number(runId);
	const dispatch = useDispatch();

	const { rows, zone_stats, loading } = useSelector(
		(state: RootState) => state.backtest.decisionMatrix
	);
	const runStatus = useSelector(
		(state: RootState) => state.backtest.currentRun?.status
	);

	useEffect(() => {
		dispatch(fetchDecisionMatrixRequest({ backtestId, runId: runIdNum }));
	}, [backtestId, runIdNum]);

	useEffect(() => {
		if (runStatus === "DONE") {
			dispatch(fetchDecisionMatrixRequest({ backtestId, runId: runIdNum }));
		}
	}, [runStatus]);

	if (loading) return <Spin className="flex justify-center p-8" />;

	const byZone: Record<string, DecisionMatrixRow[]> = {};
	for (const row of rows) {
		const z = row.zone ?? "UNKNOWN";
		if (!byZone[z]) byZone[z] = [];
		byZone[z].push(row);
	}

	const zoneOrder = ["A", "B", "C", "D", "UNKNOWN"];
	const presentZones = zoneOrder.filter((z) => byZone[z]?.length);

	if (presentZones.length === 0) {
		return (
			<Card title="Decision Matrix">
				<Empty description="Nessun dato — esegui il backtest per popolare la matrice" />
			</Card>
		);
	}

	const collapseItems = presentZones.map((z) => {
		const meta = ZONE_META[z] ?? { label: `Zone ${z}`, description: "", color: "#999" };
		const zoneRows = byZone[z];
		const totalCount = zoneRows.reduce((sum, r) => sum + r.count, 0);
		const openCount = zoneRows
			.filter((r) => r.decision_action === "OPEN")
			.reduce((sum, r) => sum + r.count, 0);
		const stat: ZoneStat | undefined = zone_stats[z];

		return {
			key: z,
			label: (
				<div className="flex items-center gap-3 w-full">
					<span style={{ color: meta.color }} className="font-bold">{meta.label}</span>
					<span className="text-xs text-gray-400">{meta.description}</span>
					<div className="ml-auto flex items-center gap-4">
						{stat && (
							<>
								<Tooltip title={`Win Rate su ${stat.n_closed} posizioni chiuse`}>
									<span className="text-xs">
										WR <b style={{ color: stat.win_rate >= 50 ? "#52c41a" : "#fa8c16" }}>{stat.win_rate.toFixed(0)}%</b>
									</span>
								</Tooltip>
								<Tooltip title="P&L medio per trade chiuso">
									<span className="text-xs">
										Avg P&L <b style={{ color: stat.avg_pnl >= 0 ? "#52c41a" : "#ff4d4f" }}>{stat.avg_pnl >= 0 ? "+" : ""}{stat.avg_pnl.toFixed(0)}</b>
									</span>
								</Tooltip>
								<Tooltip title="Max Drawdown cumulativo su P&L sequenziali per zona">
									<span className="text-xs text-gray-500">
										Max DD <b>{stat.max_drawdown.toFixed(0)}</b>
									</span>
								</Tooltip>
							</>
						)}
						<Tag color="success">{openCount} OPEN</Tag>
						<Tag color="default">{totalCount} tot</Tag>
					</div>
				</div>
			),
			children: <ZoneContent rows={zoneRows} />,
			style: { borderLeft: `4px solid ${meta.color}`, marginBottom: 8 },
		};
	});

	return (
		<Card title="Decision Matrix — Regime × Strategy × Decision">
			<Collapse
				items={collapseItems}
				defaultActiveKey={presentZones}
				bordered={false}
				style={{ background: "transparent" }}
			/>
		</Card>
	);
};

export default DecisionMatrix;
