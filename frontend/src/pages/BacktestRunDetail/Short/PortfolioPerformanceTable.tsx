import { Card, Table } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../../store/reducers";
import { ColumnsType } from "antd/es/table";
import { fetchPortfolioPerformanceRequest } from "../../../features/backtest/reducer";
import {
	formatCurrency,
	formatPercent,
	formatNumber,
	formatDelta,
} from "../../../utils/number";

type PortfolioRow = {
	snapshot_date: string;
	cash: number;
	positions_value: number;
	total_equity: number;
	realized_pnl: number;
	unrealized_pnl: number;
	total_pnl: number;
	total_delta: number;
	total_gamma: number;
	total_theta: number;
	total_vega: number;
	open_positions_count: number;
	closed_positions_count: number;
	new_positions_count: number;
	underlying_price: number;
	iv: number;
};

function buildPortfolioColumns(): ColumnsType<PortfolioRow> {
	return [
		{
			title: "Date",
			dataIndex: "snapshot_date",
			key: "snapshot_date",
			width: 110,
			render: (date: string) => date,
		},
		{
			title: "Cash",
			key: "cash",
			width: 100,
			render: (_: unknown, row: PortfolioRow) =>
				formatCurrency(row.cash),
		},
		{
			title: "Positions",
			key: "positions_value",
			width: 100,
			render: (_: unknown, row: PortfolioRow) =>
				formatCurrency(row.positions_value),
		},
		{
			title: "Total Equity",
			key: "total_equity",
			width: 110,
			render: (_: unknown, row: PortfolioRow) =>
				formatCurrency(row.total_equity),
		},
		{
			title: "Realized P&L",
			key: "realized_pnl",
			width: 110,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.realized_pnl),
		},
		{
			title: "Unrealized P&L",
			key: "unrealized_pnl",
			width: 110,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.unrealized_pnl),
		},
		{
			title: "Total P&L",
			key: "total_pnl",
			width: 110,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.total_pnl),
		},
		{
			title: "Delta",
			key: "total_delta",
			width: 80,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.total_delta),
		},
		{
			title: "Gamma",
			key: "total_gamma",
			width: 80,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.total_gamma),
		},
		{
			title: "Theta",
			key: "total_theta",
			width: 80,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.total_theta),
		},
		{
			title: "Vega",
			key: "total_vega",
			width: 80,
			render: (_: unknown, row: PortfolioRow) =>
				formatDelta(row.total_vega),
		},
		{
			title: "Open",
			key: "open_positions_count",
			width: 60,
			render: (_: unknown, row: PortfolioRow) =>
				row.open_positions_count,
		},
		{
			title: "Closed",
			key: "closed_positions_count",
			width: 60,
			render: (_: unknown, row: PortfolioRow) =>
				row.closed_positions_count,
		},
		{
			title: "New",
			key: "new_positions_count",
			width: 60,
			render: (_: unknown, row: PortfolioRow) =>
				row.new_positions_count,
		},
		{
			title: "Underlying",
			key: "underlying_price",
			width: 100,
			render: (_: unknown, row: PortfolioRow) =>
				formatNumber(row.underlying_price, 2),
		},
		{
			title: "IV",
			key: "iv",
			width: 70,
			render: (_: unknown, row: PortfolioRow) =>
				formatPercent(row.iv),
		},
	];
}

const PortfolioPerformanceTable = () => {
	const dispatch = useDispatch();
	const { portfolioPerformances, currentRun, loading, current } = useSelector(
		(state: RootState) => state.backtest
	);

	const isDone = currentRun?.status === "DONE";
	const backtestId = current?.id || currentRun?.backtest_id;
	const runId = currentRun?.id;

	const handlePaginationChange = (page: number, pageSize: number) => {
		if (backtestId && runId) {
			dispatch(
				fetchPortfolioPerformanceRequest({
					backtestId,
					runId,
					page,
					limit: pageSize,
				})
			);
		}
	};

	return (
		<Card size="small" title="Portfolio Performance">
			<Table
				rowKey="snapshot_date"
				size="small"
				columns={buildPortfolioColumns()}
				dataSource={portfolioPerformances.items}
				loading={loading}
				pagination={{
					current: portfolioPerformances.page,
					pageSize: portfolioPerformances.page_size,
					total: portfolioPerformances.total,
					showTotal: (t) => `${t} records`,
					onChange: handlePaginationChange,
				}}
				locale={{
					emptyText: isDone
						? "No portfolio performance data"
						: "Run the backtest to see portfolio performance",
				}}
				scroll={{ x: 1500 }}
			/>
		</Card>
	);
};

export default PortfolioPerformanceTable;
