import { useMemo } from "react";
import { Group } from "@visx/group";
import { LinePath, Bar } from "@visx/shape";
import { scaleLinear, scaleBand, scaleTime } from "@visx/scale";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";
import { useParentSize } from "@visx/responsive";
import { LegendOrdinal } from "@visx/legend";
import { scaleOrdinal } from "@visx/scale";
import { curveMonotoneX } from "@visx/curve";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DataPoint = {
	date: Date;
	value: number;
};

export type Series = {
	key: string;
	label: string;
	data: DataPoint[];
	type: "line" | "bar";
	color: string;
};

type TooltipData = {
	date: Date;
	entries: { label: string; value: number; color: string }[];
};

type Props = {
	series: Series[];
	height?: number;
	showLegend?: boolean;
	yTickFormat?: (v: number) => string;
	xTickFormat?: (d: Date) => string;
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MARGIN = { top: 16, right: 24, bottom: 40, left: 56 };
const TOOLTIP_STYLES = {
	...defaultStyles,
	background: "#1f2937",
	border: "1px solid #374151",
	borderRadius: 6,
	color: "#f9fafb",
	fontSize: 12,
	padding: "8px 12px",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function allDates(series: Series[]): Date[] {
	const set = new Map<number, Date>();
	series.forEach((s) => s.data.forEach((d) => set.set(d.date.getTime(), d.date)));
	return Array.from(set.values()).sort((a, b) => a.getTime() - b.getTime());
}

function yDomain(series: Series[]): [number, number] {
	let min = Infinity;
	let max = -Infinity;
	series.forEach((s) =>
		s.data.forEach((d) => {
			if (d.value < min) min = d.value;
			if (d.value > max) max = d.value;
		})
	);
	const pad = (max - min) * 0.1 || 1;
	return [Math.min(min - pad, 0), max + pad];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Chart({
	series,
	height = 320,
	showLegend = true,
	yTickFormat = (v) => String(v),
	xTickFormat = (d) => d.toLocaleDateString("it-IT", { month: "short", year: "2-digit" }),
}: Props) {
	const { parentRef, width } = useParentSize({ debounceTime: 50 });

	const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
	const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);

	const dates = useMemo(() => allDates(series), [series]);

	const xScaleBand = useMemo(
		() => scaleBand<Date>({ domain: dates, range: [0, innerW], padding: 0.2 }),
		[dates, innerW]
	);

	const xScaleTime = useMemo(
		() =>
			scaleTime<number>({
				domain: [dates[0] ?? new Date(), dates[dates.length - 1] ?? new Date()],
				range: [0, innerW],
			}),
		[dates, innerW]
	);

	const yScale = useMemo(
		() => scaleLinear<number>({ domain: yDomain(series), range: [innerH, 0], nice: true }),
		[series, innerH]
	);

	const colorScale = useMemo(
		() =>
			scaleOrdinal<string, string>({
				domain: series.map((s) => s.label),
				range: series.map((s) => s.color),
			}),
		[series]
	);

	const { showTooltip, hideTooltip, tooltipData, tooltipLeft, tooltipTop, tooltipOpen } =
		useTooltip<TooltipData>();

	const handleMouseMove = (e: React.MouseEvent<SVGRectElement>) => {
		const svgX = e.nativeEvent.offsetX - MARGIN.left;
		// trova la data più vicina
		const closest = dates.reduce((prev, curr) => {
			const px = xScaleTime(prev);
			const cx = xScaleTime(curr);
			return Math.abs(cx - svgX) < Math.abs(px - svgX) ? curr : prev;
		});

		const entries = series
			.map((s) => {
				const point = s.data.find((d) => d.date.getTime() === closest.getTime());
				return point ? { label: s.label, value: point.value, color: s.color } : null;
			})
			.filter(Boolean) as TooltipData["entries"];

		showTooltip({
			tooltipData: { date: closest, entries },
			tooltipLeft: xScaleTime(closest) + MARGIN.left,
			tooltipTop: e.nativeEvent.offsetY,
		});
	};

	const hasBars = series.some((s) => s.type === "bar");

	return (
		<div className="w-full">
			{showLegend && series.length > 1 && (
				<div className="mb-2 flex gap-4 flex-wrap">
					<LegendOrdinal scale={colorScale}>
						{(labels: { datum: string; index: number; text: string; value?: string }[]) => (
							<div className="flex gap-4 flex-wrap">
								{labels.map((label: { datum: string; index: number; text: string; value?: string }) => (
									<div key={label.text} className="flex items-center gap-1 text-xs text-gray-500">
										<span
											className="inline-block w-3 h-3 rounded-sm"
											style={{ background: label.value }}
										/>
										{label.text}
									</div>
								))}
							</div>
						)}
					</LegendOrdinal>
				</div>
			)}

			<div ref={parentRef} style={{ width: "100%", height, position: "relative" }}>
				<svg width={width} height={height}>
					<Group left={MARGIN.left} top={MARGIN.top}>
						<GridRows scale={yScale} width={innerW} stroke="#374151" strokeOpacity={0.3} />

						{/* Bar series */}
						{series
							.filter((s) => s.type === "bar")
							.map((s) =>
								s.data.map((d, i) => {
									const bw = xScaleBand.bandwidth() / series.filter((x) => x.type === "bar").length;
									const x = (xScaleBand(d.date) ?? 0) + i * bw;
									const y = yScale(Math.max(d.value, 0));
									const barH = Math.abs(yScale(0) - yScale(d.value));
									return (
										<Bar
											key={`${s.key}-${i}`}
											x={x}
											y={y}
											width={bw - 1}
											height={barH}
											fill={s.color}
											opacity={0.8}
										/>
									);
								})
							)}

						{/* Line series */}
						{series
							.filter((s) => s.type === "line")
							.map((s) => (
								<LinePath<DataPoint>
									key={s.key}
									data={s.data}
									x={(d: DataPoint) => xScaleTime(d.date)}
									y={(d: DataPoint) => yScale(d.value)}
									stroke={s.color}
									strokeWidth={2}
									curve={curveMonotoneX}
								/>
							))}

						<AxisLeft
							scale={yScale}
							tickFormat={(v) => yTickFormat(Number(v))}
							stroke="#6b7280"
							tickStroke="#6b7280"
							tickLabelProps={{ fill: "#9ca3af", fontSize: 11 }}
						/>
						<AxisBottom
							scale={hasBars ? xScaleBand : xScaleTime}
							top={innerH}
							tickFormat={(v) => xTickFormat(v instanceof Date ? v : new Date(Number(v)))}
							stroke="#6b7280"
							tickStroke="#6b7280"
							tickLabelProps={{ fill: "#9ca3af", fontSize: 11 }}
							numTicks={Math.min(dates.length, 8)}
						/>

						{/* overlay trasparente per catturare mouse events */}
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
						{tooltipData.entries.map((e: { label: string; value: number; color: string }) => (
							<div key={e.label} className="flex items-center gap-2">
								<span
									className="inline-block w-2 h-2 rounded-full"
									style={{ background: e.color }}
								/>
								<span className="text-gray-300">{e.label}:</span>
								<span className="font-semibold">{yTickFormat(e.value)}</span>
							</div>
						))}
					</TooltipWithBounds>
				)}
			</div>
		</div>
	);
}
