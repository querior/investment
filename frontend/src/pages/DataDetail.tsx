import { useNavigate, useParams } from "react-router-dom";
import { Button, Card, Col, Descriptions, Row } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { Chart } from "../components/charts";
import type { Series } from "../components/charts";
import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { getSeriesForSymbolRequest } from "../features/data/reducer";
import { RootState } from "../store/reducers";

type Range = "1Y" | "5Y" | "10Y" | "ALL";

const RANGES: Range[] = ["1Y", "5Y", "10Y", "ALL"];

function cutoffIso(range: Range): string | undefined {
	const now = new Date();
	if (range === "1Y")  return new Date(now.getFullYear() - 1,  now.getMonth(), now.getDate()).toISOString().slice(0, 10);
	if (range === "5Y")  return new Date(now.getFullYear() - 5,  now.getMonth(), now.getDate()).toISOString().slice(0, 10);
	if (range === "10Y") return new Date(now.getFullYear() - 10, now.getMonth(), now.getDate()).toISOString().slice(0, 10);
	return undefined;
}

export default function DataDetail() {
	const { id } = useParams<{ id: string }>();
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { currentSeries } = useSelector((state: RootState) => state.data);
	const [range, setRange] = useState<Range>("5Y");

	const symbol = id ?? null;

	useEffect(() => {
		if (symbol) dispatch(getSeriesForSymbolRequest({ symbol, startDate: cutoffIso("5Y") }));
	}, [dispatch, symbol]);

	const handleRangeChange = (r: Range) => {
		setRange(r);
		if (symbol) dispatch(getSeriesForSymbolRequest({ symbol, startDate: cutoffIso(r) }));
	};

	const points =
		currentSeries?.points?.map((p) => ({ date: new Date(p.date), value: p.value })) ?? [];

	return (
		<div className="p-6 space-y-6">
			<Button
				icon={<ArrowLeftOutlined />}
				type="text"
				onClick={() => navigate("/analysis/data")}
			>
				Back to catalog
			</Button>

			<Row gutter={16}>
				<Col span={18}>
					<div className="flex justify-end gap-1 mb-2">
						{RANGES.map((r) => (
							<Button
								key={r}
								size="small"
								type={range === r ? "primary" : "text"}
								onClick={() => handleRangeChange(r)}
							>
								{r}
							</Button>
						))}
					</div>
					<Chart
						series={[
							{
								key: "series",
								label: "Value",
								type: "line",
								color: "#3b82f6",
								data: points,
							},
						]}
						height={320}
						showLegend={false}
					/>
				</Col>
				<Col span={6}>
					<Card title={currentSeries?.description} size="small">
						<Descriptions column={1} size="small">
							<Descriptions.Item label="Symbol">{symbol}</Descriptions.Item>
							<Descriptions.Item label="Source">
								{currentSeries?.source}
							</Descriptions.Item>
							<Descriptions.Item label="Frequency">
								{currentSeries?.frequency}
							</Descriptions.Item>
							<Descriptions.Item label="First date">
								{currentSeries?.first_date}
							</Descriptions.Item>
							<Descriptions.Item label="Last date">
								{currentSeries?.last_date}
							</Descriptions.Item>
							<Descriptions.Item label="Total points">
								{currentSeries?.row_count}
							</Descriptions.Item>
							<Descriptions.Item label="Category">
								{currentSeries?.data_category}
							</Descriptions.Item>
						</Descriptions>
					</Card>
				</Col>
			</Row>
		</div>
	);
}
