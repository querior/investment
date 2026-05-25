import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useParams } from "react-router-dom";
import { Button, Card, Table, Space, Tag, Select, InputNumber, DatePicker } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import {
	fetchDecisionLogsRequest,
	setDecisionLogsFilters,
} from "../../features/backtest/reducer";
import type { RootState } from "../../store/reducers";
import type { DecisionLog, DecisionLogsState } from "../../features/backtest/types";
import { getStrategyMeta } from "../../utils/strategy";

type Filters = DecisionLogsState["filters"];

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
		filters,
	} = useSelector((state: RootState) => state.backtest.decisionLogs);

	const fetchLogs = (skip: number, limit: number, f?: Filters) => {
		dispatch(
			fetchDecisionLogsRequest({
				backtestId,
				runId: runIdNum,
				skip,
				limit,
				filters: f ?? filters,
			})
		);
	};

	useEffect(() => {
		fetchLogs(0, page_size, filters);
	}, [backtestId, runIdNum]);

	const updateFilters = (patch: Partial<NonNullable<Filters>>) => {
		const next: Filters = { ...filters, ...patch };
		dispatch(setDecisionLogsFilters(next));
		fetchLogs(0, page_size, next);
	};

	const handlePageChange = (newPage: number, newPageSize: number) => {
		fetchLogs((newPage - 1) * newPageSize, newPageSize);
	};

	const STRATEGY_OPTIONS = [
		"bull_put_spread", "bear_call_spread", "put_broken_wing_butterfly",
		"bull_call_spread", "bear_put_spread", "long_straddle", "long_strangle",
		"iron_condor", "iron_butterfly", "calendar_spread", "jade_lizard",
		"reverse_jade_lizard", "diagonal_spread",
	].map((s) => {
		const meta = getStrategyMeta(s);
		return { label: meta?.acronym ?? s, value: s };
	});

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
			width: 110,
			render: (value: string | null) => {
				if (!value || value === "N/A" || value === "no_trade") return <span className="text-gray-300">—</span>;
				const meta = getStrategyMeta(value);
				if (meta) return <Tag color={meta.color}>{meta.acronym}</Tag>;
				return <span className="text-xs text-gray-500">{value}</span>;
			},
		},
		{
			title: "Entry Score",
			dataIndex: "entry_score",
			key: "entry_score",
			width: 100,
			render: (value: number | null) => value != null ? value.toFixed(1) : "—",
		},
		{
			title: "Size %",
			dataIndex: "size_multiplier",
			key: "size_multiplier",
			width: 80,
			render: (value: number) => `${(value * 100).toFixed(0)}%`,
		},
		{
			title: "Zone",
			dataIndex: "zone",
			key: "zone",
			width: 60,
			render: (value: string | null) => value ?? "—",
		},
		{
			title: "Trend",
			dataIndex: "trend",
			key: "trend",
			width: 60,
			render: (value: string | null) => value ?? "—",
		},
		{
			title: "IV Rank",
			dataIndex: "iv_rank",
			key: "iv_rank",
			width: 80,
			render: (value: number | null) => value != null ? value.toFixed(1) : "—",
		},
		{
			title: "ADX",
			dataIndex: "adx",
			key: "adx",
			width: 70,
			render: (value: number | null) => value != null ? value.toFixed(1) : "—",
		},
		{
			title: "Decision",
			dataIndex: "decision_action",
			key: "decision_action",
			width: 100,
			render: (value: string) => {
				const colors: Record<string, string> = {
					OPEN: "green",
					MONITOR: "orange",
					SKIP: "red",
				};
				return <Tag color={colors[value] ?? "default"}>{value}</Tag>;
			},
		},
		{
			title: "Score",
			dataIndex: "decision_score",
			key: "decision_score",
			width: 80,
			render: (value: number | null) => value != null ? value.toFixed(1) : "—",
		},
		{
			title: "Reasoning",
			dataIndex: "decision_reasoning",
			key: "decision_reasoning",
			width: 250,
			render: (value: string | null) =>
				value ? (
					<span className="text-xs text-gray-600">{value.substring(0, 80)}…</span>
				) : "—",
		},
	];

	return (
		<Card title="Decision Logs Analysis" loading={loading}>
			<Space direction="vertical" style={{ width: "100%" }} size="middle">
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
							value={filters?.decision_actions ?? []}
							onChange={(v) => updateFilters({ decision_actions: v.length > 0 ? v : undefined })}
							style={{ width: 200 }}
						/>
						<Select
							mode="multiple"
							placeholder="Strategia"
							options={STRATEGY_OPTIONS}
							value={filters?.strategy_names ?? []}
							onChange={(v) => updateFilters({ strategy_names: v.length > 0 ? v : undefined })}
							style={{ width: 200 }}
						/>
						<DatePicker.RangePicker
							placeholder={["Data da", "Data a"]}
							value={[
								filters?.date_from ? dayjs(filters.date_from) : null,
								filters?.date_to ? dayjs(filters.date_to) : null,
							]}
							onChange={(_, strs) =>
								updateFilters({
									date_from: strs[0] || undefined,
									date_to: strs[1] || undefined,
								})
							}
							style={{ width: 240 }}
						/>
						<Space>
							<InputNumber
								placeholder="Entry score min"
								min={0} max={100} step={5}
								value={filters?.min_entry_score ?? null}
								onChange={(v) => updateFilters({ min_entry_score: v ?? undefined })}
								style={{ width: 140 }}
							/>
							<InputNumber
								placeholder="Entry score max"
								min={0} max={100} step={5}
								value={filters?.max_entry_score ?? null}
								onChange={(v) => updateFilters({ max_entry_score: v ?? undefined })}
								style={{ width: 140 }}
							/>
						</Space>
						<Button
							onClick={() => {
								dispatch(setDecisionLogsFilters({}));
								fetchLogs(0, page_size, {});
							}}
						>
							Reset
						</Button>
						<Button icon={<DownloadOutlined />} disabled>Export</Button>
					</Space>
				</Card>

				<Table<DecisionLog>
					columns={columns}
					dataSource={logs}
					rowKey={(row) => row.id}
					pagination={{
						current: page,
						pageSize: page_size,
						total,
						showSizeChanger: true,
						pageSizeOptions: ["20", "50", "100"],
						onChange: handlePageChange,
					}}
					scroll={{ x: 1200 }}
					size="small"
				/>
			</Space>
		</Card>
	);
};

export default DecisionLogsViewer;
