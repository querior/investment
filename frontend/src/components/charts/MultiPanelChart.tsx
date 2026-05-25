import { useMemo } from "react";
import { Group } from "@visx/group";
import { LinePath } from "@visx/shape";
import { scaleLinear, scaleTime } from "@visx/scale";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { GridRows } from "@visx/grid";
import { useTooltip, TooltipWithBounds, defaultStyles } from "@visx/tooltip";
import { useParentSize } from "@visx/responsive";
import { curveMonotoneX } from "@visx/curve";

export type PanelDef = {
	label: string;
	color: string;
	data: Array<{ date: Date; value: number }>;
	yTickFormat?: (v: number) => string;
	height: number;
};

type TooltipData = {
	date: Date;
	entries: Array<{ label: string; value: number; color: string; fmt: (v: number) => string }>;
};

type Props = {
	panels: PanelDef[];
	xTickFormat?: (d: Date) => string;
};

const MARGIN = { top: 8, right: 16, bottom: 40, left: 64 };
const GAP = 10;

const TOOLTIP_STYLES = {
	...defaultStyles,
	background: "#1f2937",
	border: "1px solid #374151",
	borderRadius: 6,
	color: "#f9fafb",
	fontSize: 12,
	padding: "8px 12px",
};

export default function MultiPanelChart({
	panels,
	xTickFormat = (d) =>
		d.toLocaleDateString("it-IT", { month: "short", year: "2-digit" }),
}: Props) {
	const { parentRef, width } = useParentSize({ debounceTime: 50 });

	const innerW = Math.max(0, width - MARGIN.left - MARGIN.right);
	const totalInnerH =
		panels.reduce((sum, p) => sum + p.height, 0) +
		(panels.length - 1) * GAP;
	const totalH = MARGIN.top + totalInnerH + MARGIN.bottom;

	const panelOffsets = useMemo(() => {
		const offsets: number[] = [];
		let acc = 0;
		for (const p of panels) {
			offsets.push(acc);
			acc += p.height + GAP;
		}
		return offsets;
	}, [panels]);

	const allDates = useMemo(() => {
		const map = new Map<number, Date>();
		panels.forEach((p) => p.data.forEach((d) => map.set(d.date.getTime(), d.date)));
		return Array.from(map.values()).sort((a, b) => a.getTime() - b.getTime());
	}, [panels]);

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

	const yScales = useMemo(
		() =>
			panels.map((p) => {
				const vals = p.data.map((d) => d.value);
				if (!vals.length) return scaleLinear<number>({ domain: [0, 1], range: [p.height, 0] });
				const min = Math.min(...vals);
				const max = Math.max(...vals);
				const pad = (max - min) * 0.1 || 1;
				return scaleLinear<number>({
					domain: [min - pad, max + pad],
					range: [p.height, 0],
					nice: true,
				});
			}),
		[panels]
	);

	const { showTooltip, hideTooltip, tooltipData, tooltipLeft, tooltipTop, tooltipOpen } =
		useTooltip<TooltipData>();

	const handleMouseMove = (e: React.MouseEvent<SVGRectElement>) => {
		const svgX = e.nativeEvent.offsetX - MARGIN.left;
		if (!allDates.length) return;
		const closest = allDates.reduce((prev, curr) =>
			Math.abs(xScale(curr) - svgX) < Math.abs(xScale(prev) - svgX) ? curr : prev
		);

		const entries = panels
			.map((p, i) => {
				const point = p.data.find((d) => d.date.getTime() === closest.getTime());
				if (!point) return null;
				return {
					label: p.label,
					value: point.value,
					color: p.color,
					fmt: p.yTickFormat ?? ((v: number) => v.toFixed(2)),
				};
			})
			.filter((e): e is NonNullable<typeof e> => e !== null);

		showTooltip({
			tooltipData: { date: closest, entries },
			tooltipLeft: xScale(closest) + MARGIN.left,
			tooltipTop: e.nativeEvent.offsetY,
		});
	};

	return (
		<div ref={parentRef} style={{ width: "100%", position: "relative" }}>
			<svg width={width} height={totalH}>
				<Group left={MARGIN.left} top={MARGIN.top}>
					{panels.map((panel, i) => (
						<Group key={panel.label} top={panelOffsets[i]}>
							<text x={0} y={-3} fill="#9ca3af" fontSize={10}>
								{panel.label}
							</text>

							<GridRows
								scale={yScales[i]}
								width={innerW}
								stroke="#374151"
								strokeOpacity={0.3}
							/>

							<LinePath
								data={panel.data}
								x={(d) => xScale(d.date)}
								y={(d) => yScales[i](d.value)}
								stroke={panel.color}
								strokeWidth={1.5}
								curve={curveMonotoneX}
							/>

							<AxisLeft
								scale={yScales[i]}
								tickFormat={(v) =>
									panel.yTickFormat
										? panel.yTickFormat(Number(v))
										: Number(v).toFixed(1)
								}
								stroke="#6b7280"
								tickStroke="#6b7280"
								tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
								numTicks={3}
							/>
						</Group>
					))}

					<AxisBottom
						scale={xScale}
						top={totalInnerH}
						tickFormat={(v) =>
							xTickFormat(v instanceof Date ? v : new Date(Number(v)))
						}
						stroke="#6b7280"
						tickStroke="#6b7280"
						tickLabelProps={{ fill: "#9ca3af", fontSize: 10 }}
						numTicks={Math.min(allDates.length, 8)}
					/>

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
				<TooltipWithBounds
					left={tooltipLeft}
					top={tooltipTop}
					style={TOOLTIP_STYLES}
				>
					<div className="text-gray-400 mb-1 text-xs">
						{tooltipData.date.toLocaleDateString("it-IT")}
					</div>
					{tooltipData.entries.map((e) => (
						<div key={e.label} className="flex items-center gap-2">
							<span
								className="inline-block w-2 h-2 rounded-full flex-shrink-0"
								style={{ background: e.color }}
							/>
							<span className="text-gray-300">{e.label}:</span>
							<span className="font-semibold">{e.fmt(e.value)}</span>
						</div>
					))}
				</TooltipWithBounds>
			)}
		</div>
	);
}
