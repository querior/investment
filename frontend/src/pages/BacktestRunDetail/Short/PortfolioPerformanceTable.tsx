import { Card, Table, Tag } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../../store/reducers";
import { ColumnsType } from "antd/es/table";
import { fetchPortfolioPerformanceRequest } from "../../../features/backtest/reducer";
import { BacktestPositionDto } from "../../../features/backtest/types";
import {
	formatCurrency,
	formatPercent,
	formatNumber,
	formatDelta,
} from "../../../utils/number";
import { PositionHistoryExpandedRow } from "./PositionHistoryExpandedRow";

function buildPositionsColumns(): ColumnsType<BacktestPositionDto> {
	return [
		{
			title: "Type",
			key: "position_type",
			width: 120,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.strategy_acronym ? (
					<Tag color={row.strategy_color}>{row.strategy_acronym}</Tag>
				) : (
					<span className="text-gray-500">{row.position_type}</span>
				),
		},
		{
			title: "Status",
			dataIndex: "status",
			key: "status",
			width: 80,
		},
		{
			title: "Opened",
			dataIndex: "opened_at",
			key: "opened_at",
			width: 110,
			render: (date: string) => date,
		},
		{
			title: "Closed",
			dataIndex: "closed_at",
			key: "closed_at",
			width: 110,
			render: (date: string | null) => date || "-",
		},
		{
			title: "Days",
			dataIndex: "days_in_trade",
			key: "days_in_trade",
			width: 70,
		},
		{
			title: "Entry S",
			key: "entry_underlying",
			width: 90,
			render: (_: unknown, row: BacktestPositionDto) =>
				formatNumber(row.entry_underlying, 2),
		},
		{
			title: "Entry IV",
			key: "entry_iv",
			width: 90,
			render: (_: unknown, row: BacktestPositionDto) =>
				formatPercent(row.entry_iv),
		},
		{
			title: "Initial Value",
			key: "initial_value",
			width: 110,
			render: (_: unknown, row: BacktestPositionDto) =>
				formatCurrency(row.initial_value),
		},
		{
			title: "Close Value",
			key: "close_value",
			width: 110,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.close_value !== null ? formatCurrency(row.close_value) : "-",
		},
		{
			title: "Realized P&L",
			key: "realized_pnl",
			width: 110,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.realized_pnl !== null ? formatDelta(row.realized_pnl) : "-",
		},
		{
			title: "Unrealized P&L",
			key: "unrealized_pnl",
			width: 110,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.unrealized_pnl !== null ? formatDelta(row.unrealized_pnl) : "-",
		},
		{
			title: "Return %",
			key: "performance_pct",
			width: 100,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.performance_pct !== null ? formatPercent(row.performance_pct) : "-",
		},
	];
}

const PositionsTable = () => {
	const dispatch = useDispatch();
	const { positions, currentRun, positionLoading, current } = useSelector(
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
		<Card size="small" title="Positions">
			<Table
				rowKey="id"
				size="small"
				columns={buildPositionsColumns()}
				dataSource={positions.items}
				loading={positionLoading}
				expandable={{
					expandedRowRender: (record) =>
						backtestId && runId ? (
							<PositionHistoryExpandedRow
								backtestId={backtestId}
								runId={runId}
								position={record}
							/>
						) : null,
				}}
				pagination={{
					current: positions.page,
					pageSize: positions.page_size,
					total: positions.total,
					showTotal: (t) => `${t} records`,
					onChange: handlePaginationChange,
				}}
				locale={{
					emptyText: isDone
						? "No positions data"
						: "Run the backtest to see positions",
				}}
				scroll={{ x: 1500 }}
			/>
		</Card>
	);
};

export default PositionsTable;
