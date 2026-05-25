import { useMemo } from "react";
import { Group } from "@visx/group";
import { Area, LinePath } from "@visx/shape";
import { scaleLinear, scaleTime } from "@visx/scale";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";
import { useParentSize } from "@visx/responsive";
import { curveMonotoneX } from "@visx/curve";

type DataPoint = { date: Date; value: number };

type Props = {
	realizedData: DataPoint[];
	unrealizedData: DataPoint[];
	height?: number;
};

const MARGIN = { top: 16, right: 16, bottom: 40, left: 72 };

const TOOLTIP_STYLES = {
	...defaultStyles,
	background: "#1f2937",
	border: "1px solid #374151",
	borderRadius: 6,
	color: "#f9fafb",
	fontSize: 12,
	padding: "8px 12px",
};

const fmt = (v: number) =>
	`${v >= 0 ? "+" : ""}$${Math.abs(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

export default function PnlAttributionChart({
	realizedData,
	unrealizedData,
	height = 308,
}: Props) {
	const { parentRef, width } = useParentSize({ debounceTime: 50 });

	const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
	const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

	const allDates = useMemo(() => {
		const map = new Map<number, Date>();
		[...realizedData, ...unrealizedData].forEach((d) =>
			map.set(d.date.getTime(), d.date)
		);
		return Array.from(map.values()).sort((a, b) => a.getTime() - b.getTime());
	}, [realizedData, unrealizedData]);

	const xScale = useMemo(
		() =>
			scaleTime<number>({
				domain: [
					allDates[0] ?? new Date(),
					allDates[allDates.length - 1] ?? new Date(),
				],
				range: [0, innerW],
			}),
		[allDates, innerW]
	);

	const yScale = useMemo(() => {
		const allVals = [
			...realizedData.map((d) => d.value),
			...unrealizedData.map((d) => d.value),
			0,
		];
		const min = Math.min(...allVals);
		const max = Math.max(...allVals);
		const pad = (max - min) * 0.1 || 100;
		return scaleLinear<number>({
			domain: [min - pad, max + pad],
			range: [innerH, 0],
			nice: true,
		});
	}, [realizedData, unrealizedData, innerH]);

	const { showTooltip, hideTooltip, tooltipData, tooltipLeft, tooltipTop, tooltipOpen } =
		useTooltip<{ date: Date; realized: number | null; unrealized: number | null }>();

	const handleMouseMove = (e: React.MouseEvent<SVGRectElement>) => {
		const svgX = e.nativeEvent.offsetX - MARGIN.left;
		if (!allDates.length) return;
		const closest = allDates.reduce((prev, curr) =>
			Math.abs(xScale(curr) - svgX) < Math.abs(xScale(prev) - svgX) ? curr : prev
		);
		const realized =
			realizedData.find((d) => d.date.getTime() === closest.getTime())?.value ?? null;
		const unrealized =
			unrealizedData.find((d) => d.date.getTime() === closest.getTime())?.value ?? null;
		showTooltip({
			tooltipData: { date: closest, realized, unrealized },
			tooltipLeft: xScale(closest) + MARGIN.left,
			tooltipTop: e.nativeEvent.offsetY,
		});
	};

	const zeroY = yScale(0);

	return (
		<div ref={parentRef} style={{ width: "100%", position: "relative" }}>
			<div className="flex gap-4 mb-2 text-xs text-gray-500">
				<span className="flex items-center gap-1">
					<span
						className="inline-block w-3 h-3 rounded-sm"
						style={{ background: "#10b981", opacity: 0.35 }}
					/>
					Realized P&L
				</span>
				<span className="flex items-center gap-1">
					<svg width={16} height={10}>
						<line
							x1={0} y1={5} x2={16} y2={5}
							stroke="#f59e0b"
							strokeWidth={2}
							strokeDasharray="4,3"
						/>
					</svg>
					Unrealized P&L
				</span>
			</div>

			<svg width={width} height={height}>
				<defs>
					<linearGradient id="realized-fill" x1="0" y1="0" x2="0" y2="1">
						<stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
						<stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
					</linearGradient>
				</defs>

				<Group left={MARGIN.left} top={MARGIN.top}>
					<GridRows
						scale={yScale}
						width={innerW}
						stroke="#374151"
						strokeOpacity={0.3}
					/>

					{/* Zero baseline */}
					<line
						x1={0} x2={innerW}
						y1={zeroY} y2={zeroY}
						stroke="#6b7280"
						strokeWidth={1}
						strokeOpacity={0.6}
					/>

					{/* Realized P&L — filled area */}
					{realizedData.length > 0 && (
						<>
							<Area
								data={realizedData}
								x={(d) => xScale(d.date)}
								y0={() => zeroY}
								y1={(d) => yScale(d.value)}
								fill="url(#realized-fill)"
								curve={curveMonotoneX}
							/>
							<LinePath
								data={realizedData}
								x={(d) => xScale(d.date)}
								y={(d) => yScale(d.value)}
								stroke="#10b981"
								strokeWidth={2}
								curve={curveMonotoneX}
							/>
						</>
					)}

					{/* Unrealized P&L — dashed line */}
					{unrealizedData.length > 0 && (
						<LinePath
							data={unrealizedData}
							x={(d) => xScale(d.date)}
							y={(d) => yScale(d.value)}
							stroke="#f59e0b"
							strokeWidth={1.5}
							strokeDasharray="6,3"
							curve={curveMonotoneX}
						/>
					)}

					<AxisLeft
						scale={yScale}
						tickFormat={(v) => fmt(Number(v))}
						stroke="#6b7280"
						tickStroke="#6b7280"
						tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
						numTicks={5}
					/>
					<AxisBottom
						scale={xScale}
						top={innerH}
						tickFormat={(v) =>
							(v instanceof Date ? v : new Date(Number(v))).toLocaleDateString(
								"it-IT",
								{ month: "short", year: "2-digit" }
							)
						}
						stroke="#6b7280"
						tickStroke="#6b7280"
						tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
						numTicks={8}
					/>

					{tooltipOpen && tooltipData && (
						<line
							x1={xScale(tooltipData.date)} x2={xScale(tooltipData.date)}
							y1={0} y2={innerH}
							stroke="#6b7280" strokeWidth={1} strokeDasharray="4,2"
							pointerEvents="none"
						/>
					)}

					<rect
						width={innerW}
						height={innerH}
						fill="transparent"
						onMouseMove={handleMouseMove}
						onMouseLeave={hideTooltip}
					/>
				</Group>
			</svg>

			{tooltipOpen && tooltipData && (
				<TooltipWithBounds
					left={tooltipLeft}
					top={tooltipTop}
					style={TOOLTIP_STYLES}
				>
					<div className="text-gray-400 mb-1 text-xs">
						{tooltipData.date.toLocaleDateString("it-IT")}
					</div>
					{tooltipData.realized !== null && (
						<div className="flex items-center gap-2">
							<span className="inline-block w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
							<span className="text-gray-300">Realized:</span>
							<span
								className={`font-semibold ${tooltipData.realized >= 0 ? "text-green-400" : "text-red-400"}`}
							>
								{fmt(tooltipData.realized)}
							</span>
						</div>
					)}
					{tooltipData.unrealized !== null && (
						<div className="flex items-center gap-2">
							<span className="inline-block w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
							<span className="text-gray-300">Unrealized:</span>
							<span
								className={`font-semibold ${tooltipData.unrealized >= 0 ? "text-green-400" : "text-red-400"}`}
							>
								{fmt(tooltipData.unrealized)}
							</span>
						</div>
					)}
				</TooltipWithBounds>
			)}
		</div>
	);
}
