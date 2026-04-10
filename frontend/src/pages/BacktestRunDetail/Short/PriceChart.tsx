import { useMemo } from "react";
import { scaleLinear, scaleTime } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { Group } from "@visx/group";
import { AxisLeft, AxisBottom } from "@visx/axis";
import { ParentSize } from "@visx/responsive";
import { BacktestPositionHistoryDto } from "../../../features/backtest/types";
import { formatNumber } from "../../../utils/number";

interface PriceChartProps {
	data: BacktestPositionHistoryDto[];
}

const MARGIN = { top: 20, right: 30, bottom: 30, left: 60 };

const PriceChartInner = ({ data, width, height }: PriceChartProps & { width: number; height: number }) => {
	const innerWidth = width - MARGIN.left - MARGIN.right;
	const innerHeight = height - MARGIN.top - MARGIN.bottom;

	const xScale = useMemo(
		() =>
			scaleTime<number>({
				domain: [
					new Date(data[0]?.snapshot_date || 0),
					new Date(data[data.length - 1]?.snapshot_date || 0),
				],
				range: [0, innerWidth],
			}),
		[data, innerWidth]
	);

	const underlyingPrices = data.map((d) => d.underlying_price);
	const positionPrices = data.map((d) => d.position_price);
	const allPrices = [...underlyingPrices, ...positionPrices];
	const minPrice = Math.min(...allPrices);
	const maxPrice = Math.max(...allPrices);
	const priceRange = maxPrice - minPrice;

	const yScale = useMemo(
		() =>
			scaleLinear<number>({
				domain: [minPrice - priceRange * 0.1, maxPrice + priceRange * 0.1],
				range: [innerHeight, 0],
			}),
		[minPrice, maxPrice, priceRange, innerHeight]
	);

	return (
		<svg width={width} height={height + 40}>
			<Group left={MARGIN.left} top={MARGIN.top}>
				{/* Grid lines */}
				<g opacity={0.4}>
					{yScale.ticks(5).map((tick) => (
						<line
							key={`grid-${tick}`}
							x1={0}
							x2={innerWidth}
							y1={yScale(tick)}
							y2={yScale(tick)}
							stroke="#666666"
						/>
					))}
				</g>

				{/* Underlying Price Line */}
				<LinePath<BacktestPositionHistoryDto>
					data={data}
					x={(d) => xScale(new Date(d.snapshot_date))}
					y={(d) => yScale(d.underlying_price)}
					stroke="#8884d8"
					strokeWidth={2}
				/>

				{/* Position Price Line */}
				<LinePath<BacktestPositionHistoryDto>
					data={data}
					x={(d) => xScale(new Date(d.snapshot_date))}
					y={(d) => yScale(d.position_price)}
					stroke="#82ca9d"
					strokeWidth={2}
				/>

				{/* Axes */}
				<AxisLeft
					scale={yScale}
					tickFormat={(value) => formatNumber(value as number, 2)}
					numTicks={5}
					tickLabelProps={() => ({
						fill: "#ffffff",
						fontSize: 12,
					})}
				/>
				<AxisBottom
					top={innerHeight}
					scale={xScale}
					numTicks={5}
					tickFormat={(date) => {
						const d = date as Date;
						return `${d.getDate()}/${d.getMonth() + 1}`;
					}}
					tickLabelProps={() => ({
						fill: "#ffffff",
						fontSize: 12,
					})}
				/>

				{/* Y-axis label */}
				<text x={-innerHeight / 2} y={-50} textAnchor="middle" transform="rotate(-90)" fontSize={12} fill="#ffffff">
					Price
				</text>
			</Group>

			{/* Legend */}
			<g>
				<rect x={MARGIN.left} y={height + 10} width={12} height={12} fill="#8884d8" />
				<text x={MARGIN.left + 18} y={height + 20} fontSize={12} fill="#ffffff">
					Underlying Price
				</text>
				<rect x={MARGIN.left + 200} y={height + 10} width={12} height={12} fill="#82ca9d" />
				<text x={MARGIN.left + 218} y={height + 20} fontSize={12} fill="#ffffff">
					Position Price
				</text>
			</g>
		</svg>
	);
};

export const PriceChart = ({ data }: PriceChartProps) => {
	return (
		<ParentSize>
			{({ width }) => (
				<PriceChartInner data={data} width={Math.max(width, 400)} height={300} />
			)}
		</ParentSize>
	);
};
