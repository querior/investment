import { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import { Button, Card, Table, Space, Tag, Select } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
	fetchDecisionLogsRequest,
	setDecisionLogsFilters,
} from "../../features/backtest/reducer";
import type { RootState } from "../../store/reducers";
import type { DecisionLog } from "../../features/backtest/types";

const DecisionLogsViewer: React.FC = () => {
	const { id, runId } = useParams<{ id: string; runId: string }>();
	const backtestId = Number(id);
	const runIdNum = Number(runId);
	const dispatch = useDispatch();

	const {
		items: logs,
		loading,
		page,
		page_size,
		total,
	} = useSelector((state: RootState) => state.backtest.decisionLogs);

	const [selectedDecisions, setSelectedDecisions] = useState<string[]>([]);

	useEffect(() => {
		dispatch(
			fetchDecisionLogsRequest({
				backtestId,
				runId: runIdNum,
				skip: 0,
				limit: 20,
			})
		);
	}, [backtestId, runIdNum, dispatch]);

	const handleFilterChange = (values: string[]) => {
		setSelectedDecisions(values);
		dispatch(
			setDecisionLogsFilters({
				decision_actions: values.length > 0 ? values : undefined,
			})
		);
		dispatch(
			fetchDecisionLogsRequest({
				backtestId,
				runId: runIdNum,
				skip: 0,
				limit: 20,
				filters: {
					decision_actions: values.length > 0 ? values : undefined,
				},
			})
		);
	};

	const columns: ColumnsType<DecisionLog> = [
		{
			title: "Data",
			dataIndex: "date",
			key: "date",
			width: 100,
			sorter: (a, b) => a.date.localeCompare(b.date),
		},
		{
			title: "Strategia",
			dataIndex: "strategy_name",
			key: "strategy_name",
			width: 150,
		},
		{
			title: "Entry Score",
			dataIndex: "entry_score",
			key: "entry_score",
			width: 100,
			render: (value) => value?.toFixed(1) || "-",
		},
		{
			title: "Size %",
			dataIndex: "size_multiplier",
			key: "size_multiplier",
			width: 80,
			render: (value) => `${(value * 100).toFixed(0)}%`,
		},
		{
			title: "Zone",
			dataIndex: "zone",
			key: "zone",
			width: 60,
			render: (value) => value || "-",
		},
		{
			title: "Trend",
			dataIndex: "trend",
			key: "trend",
			width: 60,
			render: (value) => value || "-",
		},
		{
			title: "IV Rank",
			dataIndex: "iv_rank",
			key: "iv_rank",
			width: 80,
			render: (value) => value?.toFixed(1) || "-",
		},
		{
			title: "ADX",
			dataIndex: "adx",
			key: "adx",
			width: 70,
			render: (value) => value?.toFixed(1) || "-",
		},
		{
			title: "Decision",
			dataIndex: "decision_action",
			key: "decision_action",
			width: 100,
			render: (value) => {
				const colors: Record<string, string> = {
					OPEN: "green",
					MONITOR: "orange",
					SKIP: "red",
				};
				return <Tag color={colors[value] || "default"}>{value}</Tag>;
			},
		},
		{
			title: "Score",
			dataIndex: "decision_score",
			key: "decision_score",
			width: 80,
			render: (value) => value?.toFixed(1) || "-",
		},
		{
			title: "Reasoning",
			dataIndex: "decision_reasoning",
			key: "decision_reasoning",
			width: 250,
			render: (value) =>
				value ? (
					<span className="text-xs text-gray-600">
						{value.substring(0, 80)}...
					</span>
				) : (
					"-"
				),
		},
	];

	return (
		<Card title="Decision Logs Analysis" loading={loading}>
			<Space direction="vertical" style={{ width: "100%" }} size="large">
				{/* Filters */}
				<Card size="small" title="Filtri">
					<Space wrap>
						<Select
							mode="multiple"
							placeholder="Decision Type"
							options={[
								{ label: "OPEN", value: "OPEN" },
								{ label: "MONITOR", value: "MONITOR" },
								{ label: "SKIP", value: "SKIP" },
							]}
							value={selectedDecisions}
							onChange={handleFilterChange}
							style={{ width: 200 }}
						/>
						<Button icon={<DownloadOutlined />} disabled>
							Export
						</Button>
					</Space>
				</Card>
				{/* Table */}
				<Table<DecisionLog>
					columns={columns}
					dataSource={logs}
					rowKey={(row) => row.id}
					pagination={{
						current: page,
						pageSize: page_size,
						total: total,
						onChange: (newPage, newPageSize) => {
							const skip = (newPage - 1) * newPageSize;
							dispatch(
								fetchDecisionLogsRequest({
									backtestId,
									runId: runIdNum,
									skip,
									limit: newPageSize,
								})
							);
						},
					}}
					scroll={{ x: 1500 }}
					size="small"
				/>
			</Space>
		</Card>
	);
};

export default DecisionLogsViewer;
