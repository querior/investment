import { Table, Card, Tag } from "antd";
import { StrategyPerformance, ZonePerformance } from "../../features/backtest/types";
import { fmt } from "../../utils/string";
import { getStrategyMeta } from "../../utils/strategy";

interface PerformanceTableProps {
	performances: StrategyPerformance[] | undefined;
}

const ZONE_COLOR: Record<string, string> = {
	A: "blue", B: "orange", C: "green", D: "purple", UNKNOWN: "default",
};

const pnlColor = (v: number) => (v >= 0 ? "#3f8600" : "#cf1322");

const PerformanceTable = ({ performances }: PerformanceTableProps) => {
	if (!performances || performances.length === 0) {
		return null;
	}

	const zoneColumns = [
		{
			title: "Zone",
			key: "zone",
			width: 70,
			render: (_: unknown, row: { zone: string }) => (
				<Tag color={ZONE_COLOR[row.zone] ?? "default"} style={{ fontWeight: 600 }}>
					{row.zone}
				</Tag>
			),
		},
		{
			title: "Count",
			dataIndex: "count",
			key: "count",
			width: 60,
			align: "center" as const,
		},
		{
			title: "Win",
			dataIndex: "winning",
			key: "winning",
			width: 50,
			align: "center" as const,
		},
		{
			title: "Lose",
			dataIndex: "losing",
			key: "losing",
			width: 50,
			align: "center" as const,
		},
		{
			title: "Win Rate",
			dataIndex: "win_rate",
			key: "win_rate",
			width: 85,
			align: "center" as const,
			render: (v: number) => fmt(v, true),
		},
		{
			title: "Total P&L",
			dataIndex: "total_pnl",
			key: "total_pnl",
			width: 110,
			align: "right" as const,
			render: (v: number) => <span style={{ color: pnlColor(v) }}>${v.toFixed(2)}</span>,
		},
		{
			title: "Avg P&L",
			dataIndex: "avg_pnl",
			key: "avg_pnl",
			width: 100,
			align: "right" as const,
			render: (v: number) => <span style={{ color: pnlColor(v) }}>${v.toFixed(2)}</span>,
		},
		{
			title: "Avg Days",
			dataIndex: "avg_holding_days",
			key: "avg_holding_days",
			width: 85,
			align: "center" as const,
			render: (v: number) => v.toFixed(1),
		},
	];

	const expandedRowRender = (row: StrategyPerformance) => {
		if (!row.zone_breakdown || Object.keys(row.zone_breakdown).length === 0) {
			return <span className="text-xs text-gray-400 pl-4">Nessun dato per zona disponibile</span>;
		}
		const zoneData = Object.entries(row.zone_breakdown)
			.sort(([a], [b]) => a.localeCompare(b))
			.map(([zone, stats]: [string, ZonePerformance]) => ({ key: zone, zone, ...stats }));

		return (
			<div className="pl-8 py-1">
				<Table
					columns={zoneColumns}
					dataSource={zoneData}
					pagination={false}
					size="small"
					showHeader={true}
					style={{ background: "transparent" }}
				/>
			</div>
		);
	};

	const columns = [
		{
			title: "Strategy",
			key: "strategy",
			width: 150,
			render: (_: unknown, row: StrategyPerformance) => {
				const acronym = row.strategy_acronym;
				const color = row.strategy_color;
				if (acronym && color && color !== "default") {
					return <Tag color={color}>{acronym}</Tag>;
				}
				const meta = getStrategyMeta(row.strategy);
				if (meta) return <Tag color={meta.color}>{meta.acronym}</Tag>;
				return <span className="text-gray-500 text-xs">{row.strategy_name ?? row.strategy}</span>;
			},
		},
		{
			title: "Count",
			dataIndex: "count",
			key: "count",
			width: 80,
			align: "center" as const,
		},
		{
			title: "Winning",
			dataIndex: "winning",
			key: "winning",
			width: 80,
			align: "center" as const,
		},
		{
			title: "Losing",
			dataIndex: "losing",
			key: "losing",
			width: 80,
			align: "center" as const,
		},
		{
			title: "Win Rate",
			dataIndex: "win_rate",
			key: "win_rate",
			width: 100,
			align: "center" as const,
			render: (value: number) => fmt(value, true),
		},
		{
			title: "Avg Days",
			dataIndex: "avg_holding_days",
			key: "avg_holding_days",
			width: 100,
			align: "center" as const,
			render: (value: number) => value.toFixed(1),
		},
		{
			title: "Total P&L",
			dataIndex: "total_pnl",
			key: "total_pnl",
			width: 120,
			align: "right" as const,
			render: (value: number) => (
				<span style={{ color: pnlColor(value) }}>${value.toFixed(2)}</span>
			),
		},
		{
			title: "Avg P&L",
			dataIndex: "avg_pnl",
			key: "avg_pnl",
			width: 120,
			align: "right" as const,
			render: (value: number) => (
				<span style={{ color: pnlColor(value) }}>${value.toFixed(2)}</span>
			),
		},
		{
			title: "Max DD",
			dataIndex: "max_drawdown",
			key: "max_drawdown",
			width: 100,
			align: "center" as const,
			render: (value: number | null) =>
				value !== null ? `${fmt(value)}%` : "—",
		},
	];

	return (
		<Card
			size="small"
			title="Performance by Strategy"
			classNames={{ header: "!pl-0", body: "!pl-0 overflow-x-auto" }}
		>
			<Table
				columns={columns}
				dataSource={performances.map((p) => ({ ...p, key: p.strategy }))}
				pagination={false}
				size="small"
				expandable={{
					expandedRowRender,
					rowExpandable: (row) =>
						!!row.zone_breakdown && Object.keys(row.zone_breakdown).length > 0,
				}}
			/>
		</Card>
	);
};

export default PerformanceTable;
