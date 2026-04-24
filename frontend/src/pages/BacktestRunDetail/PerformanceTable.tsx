import { Table, Card, Tag } from "antd";
import { StrategyPerformance } from "../../features/backtest/types";
import { fmt } from "../../utils/string";

interface PerformanceTableProps {
	performances: StrategyPerformance[] | undefined;
}

const PerformanceTable = ({ performances }: PerformanceTableProps) => {
	if (!performances || performances.length === 0) {
		return null;
	}

	const columns = [
		{
			title: "Strategy",
			key: "strategy",
			width: 150,
			render: (_: unknown, row: StrategyPerformance) =>
				row.strategy_acronym ? (
					<Tag color={row.strategy_color}>{row.strategy_acronym}</Tag>
				) : (
					<span className="text-gray-500">{row.strategy}</span>
				),
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
				<span style={{ color: value >= 0 ? "#3f8600" : "#cf1322" }}>
					${value.toFixed(2)}
				</span>
			),
		},
		{
			title: "Avg P&L",
			dataIndex: "avg_pnl",
			key: "avg_pnl",
			width: 120,
			align: "right" as const,
			render: (value: number) => (
				<span style={{ color: value >= 0 ? "#3f8600" : "#cf1322" }}>
					${value.toFixed(2)}
				</span>
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
				dataSource={performances.map((p) => ({
					...p,
					key: p.strategy,
				}))}
				pagination={false}
				size="small"
				// scroll={{ x: 1000 }}
			/>
		</Card>
	);
};

export default PerformanceTable;
