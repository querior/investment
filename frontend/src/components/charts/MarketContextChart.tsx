import { useMemo } from "react";
import { Group } from "@visx/group";
import { LinePath } from "@visx/shape";
import { scaleLinear, scaleTime } from "@visx/scale";
import { AxisBottom, AxisLeft, AxisRight } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";
import { useParentSize } from "@visx/responsive";
import { curveMonotoneX } from "@visx/curve";

type Point = { date: Date; value: number };

type Props = {
	equityData: Point[];
	priceData: Point[];
	ivData: Point[];
	ticker?: string;
	xTickFormat?: (d: Date) => string;
};

type TooltipData = {
	date: Date;
	equity: number | null;
	price: number | null;
	iv: number | null;
};

const EQUITY_COLOR = "#10b981";
const PRICE_COLOR = "#f97316";
const IV_COLOR = "#60a5fa";

const MARGIN = { top: 16, right: 60, bottom: 36, left: 64 };
const PANEL_TOP_H = 150;
const PANEL_IV_H = 80;
const GAP = 8;

const TOOLTIP_STYLES = {
	...defaultStyles,
	background: "#1f2937",
	border: "1px solid #374151",
	borderRadius: 6,
	color: "#f9fafb",
	fontSize: 12,
	padding: "8px 12px",
};

export default function MarketContextChart({
	equityData,
	priceData,
	ivData,
	ticker = "Price",
	xTickFormat = (d) => d.toLocaleDateString("it-IT", { month: "short", year: "2-digit" }),
}: Props) {
	const { parentRef, width } = useParentSize({ debounceTime: 50 });

	const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
	const totalInnerH = PANEL_TOP_H + GAP + PANEL_IV_H;
	const totalH = MARGIN.top + totalInnerH + MARGIN.bottom;

	// Shared x-scale over all dates
	const allDates = useMemo(() => {
		const map = new Map<number, Date>();
		[equityData, priceData, ivData].forEach((series) =>
			series.forEach((d) => map.set(d.date.getTime(), d.date))
		);
		return Array.from(map.values()).sort((a, b) => a.getTime() - b.getTime());
	}, [equityData, priceData, ivData]);

	const xScale = useMemo(
		() =>
			scaleTime<number>({
				domain: [allDates[0] ?? new Date(), allDates[allDates.length - 1] ?? new Date()],
				range: [0, innerW],
			}),
		[allDates, innerW]
	);

	// Left y-scale: equity
	const yEquity = useMemo(() => {
		const vals = equityData.map((d) => d.value);
		if (!vals.length) return scaleLinear<number>({ domain: [0, 1], range: [PANEL_TOP_H, 0] });
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const pad = (max - min) * 0.08 || 1;
		return scaleLinear<number>({ domain: [min - pad, max + pad], range: [PANEL_TOP_H, 0], nice: true });
	}, [equityData]);

	// Right y-scale: symbol price
	const yPrice = useMemo(() => {
		const vals = priceData.map((d) => d.value);
		if (!vals.length) return scaleLinear<number>({ domain: [0, 1], range: [PANEL_TOP_H, 0] });
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const pad = (max - min) * 0.08 || 1;
		return scaleLinear<number>({ domain: [min - pad, max + pad], range: [PANEL_TOP_H, 0], nice: true });
	}, [priceData]);

	// IV y-scale
	const yIv = useMemo(() => {
		const vals = ivData.map((d) => d.value);
		if (!vals.length) return scaleLinear<number>({ domain: [0, 100], range: [PANEL_IV_H, 0] });
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const pad = (max - min) * 0.1 || 1;
		return scaleLinear<number>({ domain: [min - pad, max + pad], range: [PANEL_IV_H, 0], nice: true });
	}, [ivData]);

	const { showTooltip, hideTooltip, tooltipData, tooltipLeft, tooltipTop, tooltipOpen } =
		useTooltip<TooltipData>();

	const handleMouseMove = (e: React.MouseEvent<SVGRectElement>) => {
		const svgX = e.nativeEvent.offsetX - MARGIN.left;
		if (!allDates.length) return;
		const closest = allDates.reduce((prev, curr) =>
			Math.abs(xScale(curr) - svgX) < Math.abs(xScale(prev) - svgX) ? curr : prev
		);
		const t = closest.getTime();
		showTooltip({
			tooltipData: {
				date: closest,
				equity: equityData.find((d) => d.date.getTime() === t)?.value ?? null,
				price: priceData.find((d) => d.date.getTime() === t)?.value ?? null,
				iv: ivData.find((d) => d.date.getTime() === t)?.value ?? null,
			},
			tooltipLeft: xScale(closest) + MARGIN.left,
			tooltipTop: e.nativeEvent.offsetY,
		});
	};

	const ivPanelTop = PANEL_TOP_H + GAP;

	return (
		<div ref={parentRef} style={{ width: "100%", position: "relative" }}>
			{/* Legend */}
			<div className="flex gap-4 mb-1 px-1" style={{ marginLeft: MARGIN.left }}>
				<span className="flex items-center gap-1 text-xs text-gray-400">
					<span className="inline-block w-3 h-0.5 rounded" style={{ background: EQUITY_COLOR }} />
					Equity
				</span>
				<span className="flex items-center gap-1 text-xs text-gray-400">
					<span className="inline-block w-3 h-0.5 rounded" style={{ background: PRICE_COLOR }} />
					{ticker}
				</span>
				<span className="flex items-center gap-1 text-xs text-gray-400">
					<span className="inline-block w-3 h-0.5 rounded" style={{ background: IV_COLOR }} />
					IV %
				</span>
			</div>

			<svg width={width} height={totalH}>
				<Group left={MARGIN.left} top={MARGIN.top}>
					{/* ── Top panel: Equity (left) + Price (right) ── */}
					<Group top={0}>
						<GridRows scale={yEquity} width={innerW} stroke="#374151" strokeOpacity={0.3} />

						<LinePath
							data={equityData}
							x={(d) => xScale(d.date)}
							y={(d) => yEquity(d.value)}
							stroke={EQUITY_COLOR}
							strokeWidth={1.5}
							curve={curveMonotoneX}
						/>
						<LinePath
							data={priceData}
							x={(d) => xScale(d.date)}
							y={(d) => yPrice(d.value)}
							stroke={PRICE_COLOR}
							strokeWidth={1.5}
							curve={curveMonotoneX}
						/>

						<AxisLeft
							scale={yEquity}
							tickFormat={(v) => `$${Number(v).toFixed(0)}`}
							stroke="#6b7280"
							tickStroke="#6b7280"
							tickLabelProps={{ fill: "#3b82f6", fontSize: 10 }}
							numTicks={4}
						/>
						<AxisRight
							scale={yPrice}
							left={innerW}
							tickFormat={(v) => Number(v).toFixed(0)}
							stroke="#6b7280"
							tickStroke="#6b7280"
							tickLabelProps={{ fill: "#8b5cf6", fontSize: 10, dx: 4 }}
							numTicks={4}
						/>
					</Group>

					{/* ── IV panel ── */}
					<Group top={ivPanelTop}>
						<text x={0} y={-3} fill="#9ca3af" fontSize={10}>IV %</text>
						<GridRows scale={yIv} width={innerW} stroke="#374151" strokeOpacity={0.3} />
						<LinePath
							data={ivData}
							x={(d) => xScale(d.date)}
							y={(d) => yIv(d.value)}
							stroke={IV_COLOR}
							strokeWidth={1.5}
							curve={curveMonotoneX}
						/>
						<AxisLeft
							scale={yIv}
							tickFormat={(v) => `${Number(v).toFixed(0)}%`}
							stroke="#6b7280"
							tickStroke="#6b7280"
							tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
							numTicks={3}
						/>
					</Group>

					{/* ── Shared x-axis ── */}
					<AxisBottom
						scale={xScale}
						top={totalInnerH}
						tickFormat={(v) => xTickFormat(v instanceof Date ? v : new Date(Number(v)))}
						stroke="#6b7280"
						tickStroke="#6b7280"
						tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
						numTicks={Math.min(allDates.length, 8)}
					/>

					{/* Crosshair */}
					{tooltipOpen && tooltipData && (
						<line
							x1={xScale(tooltipData.date)}
							x2={xScale(tooltipData.date)}
							y1={0}
							y2={totalInnerH}
							stroke="#6b7280"
							strokeWidth={1}
							strokeDasharray="4,2"
							pointerEvents="none"
						/>
					)}

					{/* Invisible hit area */}
					<rect
						width={innerW}
						height={totalInnerH}
						fill="transparent"
						onMouseMove={handleMouseMove}
						onMouseLeave={hideTooltip}
					/>
				</Group>
			</svg>

			{tooltipOpen && tooltipData && (
				<TooltipWithBounds left={tooltipLeft} top={tooltipTop} style={TOOLTIP_STYLES}>
					<div className="text-gray-400 mb-1 text-xs">
						{tooltipData.date.toLocaleDateString("it-IT")}
					</div>
					{tooltipData.equity != null && (
						<div className="flex items-center gap-2">
							<span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: EQUITY_COLOR }} />
							<span className="text-gray-300">Equity:</span>
							<span className="font-semibold">${tooltipData.equity.toFixed(0)}</span>
						</div>
					)}
					{tooltipData.price != null && (
						<div className="flex items-center gap-2">
							<span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: PRICE_COLOR }} />
							<span className="text-gray-300">{ticker}:</span>
							<span className="font-semibold">{tooltipData.price.toFixed(2)}</span>
						</div>
					)}
					{tooltipData.iv != null && (
						<div className="flex items-center gap-2">
							<span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: IV_COLOR }} />
							<span className="text-gray-300">IV:</span>
							<span className="font-semibold">{tooltipData.iv.toFixed(1)}%</span>
						</div>
					)}
				</TooltipWithBounds>
			)}
		</div>
	);
}
