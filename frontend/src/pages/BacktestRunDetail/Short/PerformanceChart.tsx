import { useMemo } from "react";
import { scaleLinear, scaleTime } from "@visx/scale";
import { LinePath } from "@visx/shape";
import { Group } from "@visx/group";
import { AxisLeft, AxisRight, AxisBottom } from "@visx/axis";
import { ParentSize } from "@visx/responsive";
import { BacktestPositionHistoryDto } from "../../../features/backtest/types";
import { formatNumber, formatPercent } from "../../../utils/number";

interface PerformanceChartProps {
	data: BacktestPositionHistoryDto[];
}

const MARGIN = { top: 20, right: 80, bottom: 30, left: 60 };

const PerformanceChartInner = ({
	data,
	width,
	height,
}: PerformanceChartProps & { width: number; height: number }) => {
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

	// Scale for position_pnl (left axis)
	const pnlValues = data.map((d) => d.position_pnl);
	const minPnl = Math.min(...pnlValues);
	const maxPnl = Math.max(...pnlValues);
	const pnlRange = maxPnl - minPnl;

	const yScalePnl = useMemo(
		() =>
			scaleLinear<number>({
				domain: [minPnl - pnlRange * 0.1, maxPnl + pnlRange * 0.1],
				range: [innerHeight, 0],
			}),
		[minPnl, maxPnl, pnlRange, innerHeight]
	);

	// Scale for iv (right axis)
	const ivValues = data.map((d) => d.iv);
	const minIv = Math.min(...ivValues);
	const maxIv = Math.max(...ivValues);
	const ivRange = maxIv - minIv;

	const yScaleIv = useMemo(
		() =>
			scaleLinear<number>({
				domain: [minIv - ivRange * 0.1, maxIv + ivRange * 0.1],
				range: [innerHeight, 0],
			}),
		[minIv, maxIv, ivRange, innerHeight]
	);

	return (
		<svg width={width} height={height + 40}>
			<Group left={MARGIN.left} top={MARGIN.top}>
				{/* Grid lines */}
				<g opacity={0.4}>
					{yScalePnl.ticks(5).map((tick) => (
						<line
							key={`grid-${tick}`}
							x1={0}
							x2={innerWidth}
							y1={yScalePnl(tick)}
							y2={yScalePnl(tick)}
							stroke="#666666"
						/>
					))}
				</g>

				{/* Position P&L Line */}
				<LinePath<BacktestPositionHistoryDto>
					data={data}
					x={(d) => xScale(new Date(d.snapshot_date))}
					y={(d) => yScalePnl(d.position_pnl)}
					stroke="#ffc658"
					strokeWidth={2}
				/>

				{/* IV Line */}
				<LinePath<BacktestPositionHistoryDto>
					data={data}
					x={(d) => xScale(new Date(d.snapshot_date))}
					y={(d) => yScaleIv(d.iv)}
					stroke="#ff7875"
					strokeWidth={2}
				/>

				{/* Left Axis (P&L) */}
				<AxisLeft
					scale={yScalePnl}
					tickFormat={(value) => formatNumber(value as number, 2)}
					numTicks={5}
					tickLabelProps={() => ({
						fill: "#ffffff",
						fontSize: 12,
					})}
				/>

				{/* Right Axis (IV) */}
				<AxisRight
					scale={yScaleIv}
					tickFormat={(value) => formatPercent(value as number)}
					numTicks={5}
					left={innerWidth}
					tickLabelProps={() => ({
						fill: "#ffffff",
						fontSize: 12,
					})}
				/>

				{/* Bottom Axis */}
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

				{/* Y-axis labels */}
				<text x={-innerHeight / 2} y={-50} textAnchor="middle" transform="rotate(-90)" fontSize={12} fill="#ffffff">
					P&L
				</text>
				<text
					x={-innerHeight / 2}
					y={innerWidth + 50}
					textAnchor="middle"
					transform="rotate(-90)"
					fontSize={12}
					fill="#ffffff"
				>
					IV
				</text>
			</Group>

			{/* Legend */}
			<g>
				<rect x={MARGIN.left} y={height + 10} width={12} height={12} fill="#ffc658" />
				<text x={MARGIN.left + 18} y={height + 20} fontSize={12} fill="#ffffff">
					Position P&L
				</text>
				<rect x={MARGIN.left + 180} y={height + 10} width={12} height={12} fill="#ff7875" />
				<text x={MARGIN.left + 198} y={height + 20} fontSize={12} fill="#ffffff">
					IV
				</text>
			</g>
		</svg>
	);
};

export const PerformanceChart = ({ data }: PerformanceChartProps) => {
	return (
		<ParentSize>
			{({ width }) => (
				<PerformanceChartInner data={data} width={Math.max(width, 400)} height={300} />
			)}
		</ParentSize>
	);
};
