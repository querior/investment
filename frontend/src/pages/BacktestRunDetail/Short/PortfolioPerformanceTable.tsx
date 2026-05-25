import { useEffect, useState } from "react";
import { Card, Table, Tag, Tooltip, Select, Space } from "antd";
import { CheckCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../../store/reducers";
import { ColumnsType } from "antd/es/table";
import { fetchPortfolioPerformanceRequest } from "../../../features/backtest/reducer";
import { BacktestPositionDto } from "../../../features/backtest/types";
import {
	formatCurrency,
	formatPercent,
	formatDelta,
} from "../../../utils/number";
import { getPositionFilterOptionsApi } from "../../../services/backtest-service";
import { getStrategyMeta } from "../../../utils/strategy";
import { PositionHistoryExpandedRow } from "./PositionHistoryExpandedRow";

function buildPositionsColumns(): ColumnsType<BacktestPositionDto> {
	return [
		{
			title: "Type",
			key: "position_type",
			fixed: "left",
			width: 80,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.strategy_acronym ? (
					<Tooltip title={row.strategy_name ?? row.position_type}>
						<Tag color={row.strategy_color}>{row.strategy_acronym}</Tag>
					</Tooltip>
				) : (
					<span className="text-gray-500 text-xs">{row.position_type}</span>
				),
		},
		{
			title: "Status",
			dataIndex: "status",
			key: "status",
			width: 75,
			render: (s: string) => (
				<Tag color={s === "CLOSED" ? "default" : "processing"}>{s}</Tag>
			),
		},
		{
			title: "Opened",
			dataIndex: "opened_at",
			key: "opened_at",
			width: 100,
		},
		{
			title: "Closed",
			dataIndex: "closed_at",
			key: "closed_at",
			width: 100,
			render: (d: string | null) => d || "—",
		},
		{
			title: "Days",
			dataIndex: "days_in_trade",
			key: "days_in_trade",
			width: 55,
		},
		{
			title: "Regime",
			dataIndex: "entry_macro_regime",
			key: "entry_macro_regime",
			width: 90,
			render: (r: string | null) => r ? <span className="text-xs text-gray-500">{r}</span> : "—",
		},
		{
			title: "Premium (open)",
			key: "initial_value",
			width: 115,
			render: (_: unknown, row: BacktestPositionDto) => (
				<Tooltip title="Credito ricevuto (negativo) o debito pagato (positivo) all'apertura">
					<span>{formatCurrency(row.initial_value)}</span>
				</Tooltip>
			),
		},
		{
			title: "Premium (close)",
			key: "close_value",
			width: 115,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.close_value !== null ? (
					<Tooltip title="Valore della posizione alla chiusura">
						<span>{formatCurrency(row.close_value)}</span>
					</Tooltip>
				) : "—",
		},
		{
			title: "Max Loss",
			key: "entry_max_loss",
			width: 100,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.entry_max_loss != null ? (
					<Tooltip title="Perdita massima teorica per questa posizione">
						<span className="text-red-500">{formatCurrency(row.entry_max_loss)}</span>
					</Tooltip>
				) : "—",
		},
		{
			title: "Risk % cap.",
			key: "capital_at_risk_pct",
			width: 105,
			render: (_: unknown, row: BacktestPositionDto) => {
				if (row.capital_at_risk_pct == null) return "—";
				const pct = formatPercent(row.capital_at_risk_pct);
				if (row.risk_limit_ok === true) {
					return (
						<Tooltip title="Entro il limite max_risk">
							<span className="text-green-600">
								<CheckCircleOutlined className="mr-1" />{pct}
							</span>
						</Tooltip>
					);
				}
				return (
					<Tooltip title="Supera il limite max_risk configurato">
						<span className="text-red-500">
							<WarningOutlined className="mr-1" />{pct}
						</span>
					</Tooltip>
				);
			},
		},
		{
			title: "P&L",
			key: "realized_pnl",
			width: 100,
			render: (_: unknown, row: BacktestPositionDto) => {
				const pnl = row.realized_pnl ?? row.unrealized_pnl;
				return pnl !== null ? formatDelta(pnl) : "—";
			},
		},
		{
			title: "Return %",
			key: "performance_pct",
			width: 90,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.performance_pct !== null ? formatPercent(row.performance_pct) : "—",
		},
		{
			title: "P(profit)",
			key: "entry_prob_profit",
			width: 85,
			render: (_: unknown, row: BacktestPositionDto) =>
				row.entry_prob_profit != null ? (
					<Tooltip title="Probabilità di profitto stimata all'apertura">
						<span>{formatPercent(row.entry_prob_profit)}</span>
					</Tooltip>
				) : "—",
		},
	];
}

const PositionsTable = () => {
	const dispatch = useDispatch();
	const { positions, currentRun, positionLoading, current } = useSelector(
		(state: RootState) => state.backtest
	);

	const [filterStrategy, setFilterStrategy] = useState<string | undefined>();
	const [filterRegime, setFilterRegime] = useState<string | undefined>();
	const [filterOptions, setFilterOptions] = useState<{ strategies: string[]; regimes: string[] }>({ strategies: [], regimes: [] });

	const isDone = currentRun?.status === "DONE";
	const backtestId = current?.id || currentRun?.backtest_id;
	const runId = currentRun?.id;

	useEffect(() => {
		if (backtestId && runId && isDone) {
			getPositionFilterOptionsApi(backtestId, runId)
				.then(setFilterOptions)
				.catch(() => {});
		}
	}, [backtestId, runId, isDone]);

	const fetch = (page: number, pageSize: number, strategy?: string, regime?: string) => {
		if (backtestId && runId) {
			dispatch(fetchPortfolioPerformanceRequest({
				backtestId,
				runId,
				page,
				limit: pageSize,
				strategy,
				macro_regime: regime,
			}));
		}
	};

	const handlePaginationChange = (page: number, pageSize: number) => {
		fetch(page, pageSize, filterStrategy, filterRegime);
	};

	const handleStrategyChange = (val: string | undefined) => {
		setFilterStrategy(val);
		fetch(1, positions.page_size, val, filterRegime);
	};

	const handleRegimeChange = (val: string | undefined) => {
		setFilterRegime(val);
		fetch(1, positions.page_size, filterStrategy, val);
	};

	return (
		<Card
			size="small"
			title="Positions"
			extra={
				<Space>
					<Select
						allowClear
						placeholder="Strategy"
						style={{ width: 130 }}
						size="small"
						value={filterStrategy}
						onChange={handleStrategyChange}
						options={filterOptions.strategies.map((s) => {
						const meta = getStrategyMeta(s);
						return { label: meta ? meta.acronym : s, value: s };
					})}
					/>
					<Select
						allowClear
						placeholder="Regime"
						style={{ width: 130 }}
						size="small"
						value={filterRegime}
						onChange={handleRegimeChange}
						options={filterOptions.regimes.map((r) => ({ label: r, value: r }))}
					/>
				</Space>
			}
		>
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
