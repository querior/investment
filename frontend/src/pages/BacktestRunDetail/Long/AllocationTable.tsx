import { Card, Table } from "antd";
import { RunWeightDto } from "../../../features/backtest/types";
import { useSelector } from "react-redux";
import { RootState } from "../../../store/reducers";
import { ColumnsType } from "antd/es/table";
import { ArrowDownOutlined, ArrowUpOutlined } from "@ant-design/icons";

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

function RegimesCell({ row }: { row: PivotRow }) {
	if (!row.pillar_scores) return <span className="text-gray-400">—</span>;
	return (
		<span className="text-xs flex flex-wrap gap-x-2">
			{Object.entries(row.pillar_scores).map(([pillar, regime]) => {
				const isStr = typeof regime === "string";
				const label = isStr
					? (regime as string).slice(0, 3)
					: (regime as number).toFixed(2);
				const colorKey = isStr ? (regime as string) : "";
				return (
					<span
						key={pillar}
						className={REGIME_COLOR[colorKey] ?? "text-gray-400"}
					>
						{pillar[0]}={label}
					</span>
				);
			})}
		</span>
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

const AllocationTable = () => {
	const { runWeights, loading } = useSelector(
		(state: RootState) => state.backtest
	);

	const { currentRun } = useSelector((state: RootState) => state.backtest);

	const isDone = currentRun?.status === "DONE";

	return (
		<Card size="small" title="Allocations">
			{(() => {
				const rows = pivotWeights(runWeights);
				return (
					<Table
						rowKey="date"
						size="small"
						columns={buildAllocationColumns(rows)}
						dataSource={rows}
						loading={loading}
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
	);
};

export default AllocationTable;
