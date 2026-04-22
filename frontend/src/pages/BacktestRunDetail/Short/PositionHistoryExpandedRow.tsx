import { Table, Spin, Row, Col, ColumnsType, Card } from "antd";
import { useEffect, useState } from "react";
import { BacktestPositionDto, BacktestPositionHistoryDto } from "../../../features/backtest/types";
import { getPositionHistoryApi } from "../../../services/backtest-service";
import { formatCurrency, formatPercent, formatNumber, formatDelta } from "../../../utils/number";
import { PriceChart } from "./PriceChart";
import { PerformanceChart } from "./PerformanceChart";

interface PositionHeader {
	position_id: number;
	position_type: string;
	strategy_name: string | null;
	status: string;
	opened_at: string;
	closed_at: string | null;
	entry_underlying: number;
	entry_iv: number;
	entry_macro_regime: string;
	initial_value: number;
	close_value: number | null;
	realized_pnl: number | null;
	entry_criteria: string[];
	exit_criteria: string[];
}

const darkTableStyle = `
  .dark-theme-table {
    background-color: #0d1b2a !important;
  }
  .dark-theme-table .ant-table-thead > tr > th {
    background-color: #001529 !important;
    color: #ffffff !important;
    border-color: #434343 !important;
  }
  .dark-theme-table .ant-table-tbody > tr > td {
    background-color: #0d1b2a !important;
    color: #ffffff !important;
    border-color: #434343 !important;
  }
  .dark-theme-table .ant-table-tbody > tr:hover > td {
    background-color: #1f3a52 !important;
  }

  .criteria-box {
    background-color: #0d1b2a !important;
    border: 1px solid #434343;
    padding: 12px;
    border-radius: 4px;
    min-width: 250px;
  }

  .criteria-box h5 {
    color: #ffc658;
    margin-bottom: 8px;
    font-size: 12px;
    font-weight: 600;
  }

  .criteria-box ul {
    margin: 0;
    padding-left: 16px;
  }

  .criteria-box li {
    color: #ffffff;
    font-size: 12px;
    margin-bottom: 4px;
  }
`;

function buildHistoryColumns(): ColumnsType<BacktestPositionHistoryDto> {
	return [
		{
			title: "Date",
			dataIndex: "snapshot_date",
			key: "snapshot_date",
			width: 110,
		},
		{
			title: "Underlying",
			key: "underlying_price",
			width: 100,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.underlying_price, 2),
		},
		{
			title: "IV",
			key: "iv",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatPercent(row.iv),
		},
		{
			title: "Position Price",
			key: "position_price",
			width: 110,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatCurrency(row.position_price),
		},
		{
			title: "P&L",
			key: "position_pnl",
			width: 100,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatDelta(row.position_pnl),
		},
		{
			title: "Delta",
			key: "position_delta",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.position_delta, 4),
		},
		{
			title: "Gamma",
			key: "position_gamma",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.position_gamma, 4),
		},
		{
			title: "Theta",
			key: "position_theta",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.position_theta, 4),
		},
		{
			title: "Vega",
			key: "position_vega",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.position_vega, 4),
		},
		{
			title: "Min DTE",
			key: "min_dte",
			width: 80,
			render: (_: unknown, row: BacktestPositionHistoryDto) =>
				formatNumber(row.min_dte, 2),
		},
		{
			title: "Open",
			dataIndex: "is_open",
			key: "is_open",
			width: 60,
			render: (is_open: boolean) => (is_open ? "Yes" : "No"),
		},
	];
}

interface PositionHistoryExpandedRowProps {
	backtestId: number;
	runId: number;
	position: BacktestPositionDto;
}

export const PositionHistoryExpandedRow = ({
	backtestId,
	runId,
	position,
}: PositionHistoryExpandedRowProps) => {
	const [header, setHeader] = useState<PositionHeader | null>(null);
	const [history, setHistory] = useState<BacktestPositionHistoryDto[]>([]);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		const loadHistory = async () => {
			setLoading(true);
			try {
				const response = await getPositionHistoryApi(backtestId, runId, position.id);
				setHeader(response.header);
				setHistory(response.snapshots);
			} catch (error) {
				console.error("Failed to load position history:", error);
			} finally {
				setLoading(false);
			}
		};

		loadHistory();
	}, [backtestId, runId, position.id]);

	return (
		<>
			<style>{darkTableStyle}</style>
			<Spin spinning={loading}>
				{header && (
					<div style={{ marginBottom: 16, backgroundColor: "#001529", padding: "12px", borderRadius: "4px" }}>
						<Row gutter={16} style={{ marginBottom: 12 }}>
							<Col flex="auto">
								<h4 style={{ color: "#ffc658", margin: "0 0 8px 0" }}>{header.position_type}</h4>
								<div style={{ fontSize: 12, color: "#ffffff" }}>
									<p style={{ margin: "4px 0" }}>
										<strong>Status:</strong> {header.status} | <strong>Opened:</strong> {header.opened_at}
										{header.closed_at && ` | Closed: ${header.closed_at}`}
									</p>
									<p style={{ margin: "4px 0" }}>
										<strong>Entry Underlying:</strong> {formatNumber(header.entry_underlying, 2)} | <strong>Entry IV:</strong> {formatPercent(header.entry_iv)} | <strong>Macro:</strong> {header.entry_macro_regime}
									</p>
									<p style={{ margin: "4px 0" }}>
										<strong>P&L:</strong> {formatDelta(header.realized_pnl || 0)}
									</p>
								</div>
							</Col>
						</Row>

						<Row gutter={16}>
							<Col style={{ minWidth: 280 }}>
								<div className="criteria-box">
									<h5>Entry Criteria</h5>
									<ul>
										{header.entry_criteria.map((criterion, idx) => (
											<li key={idx}>{criterion}</li>
										))}
									</ul>
								</div>
							</Col>
							<Col style={{ minWidth: 280 }}>
								<div className="criteria-box">
									<h5>Exit Criteria</h5>
									<ul>
										{header.exit_criteria.map((criterion, idx) => (
											<li key={idx}>{criterion}</li>
										))}
									</ul>
								</div>
							</Col>
						</Row>
					</div>
				)}

				<Row gutter={16} style={{ width: "100%", backgroundColor: "#001529", padding: "8px", borderRadius: "4px" }}>
					<Col style={{ minWidth: 0, width: "45%", maxWidth: "45%" }}>
						<div style={{ overflowX: "auto", width: "100%" }}>
							<Table
								rowKey="snapshot_date"
								size="small"
								columns={buildHistoryColumns()}
								dataSource={history}
								pagination={false}
								scroll={{ x: 600 }}
								style={{
									backgroundColor: "#0d1b2a",
									color: "#ffffff",
								}}
								className="dark-theme-table"
							/>
						</div>
					</Col>
					<Col style={{ minWidth: 0, width: "55%", maxWidth: "55%" }}>
						<div style={{ width: "100%" }}>
							<h4 style={{ marginBottom: 16, color: "#ffffff", textAlign: "center" }}>Price</h4>
							<PriceChart data={history} />
							<h4 style={{ marginBottom: 16, marginTop: 24, color: "#ffffff", textAlign: "center" }}>Performance</h4>
							<PerformanceChart data={history} />
						</div>
					</Col>
				</Row>
			</Spin>
		</>
	);
};
