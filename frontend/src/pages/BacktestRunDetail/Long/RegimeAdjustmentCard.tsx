import { Card, Table, Tabs } from "antd";
import { ColumnsType } from "antd/es/table";
import { AdjustmentDto } from "../../../features/backtest/types";

const PILLARS = ["Growth", "Inflation", "Policy", "Risk"] as const;
const REGIMES = ["expansion", "contraction"] as const;

const RegimeAdjustmentsCard = ({
	adjustments,
	neutral,
}: {
	adjustments: AdjustmentDto[];
	neutral: Record<string, number>;
}) => {
	const assets = Object.keys(neutral);

	const tabItems = REGIMES.map((regime) => {
		const byPillarAsset: Record<string, Record<string, number>> = {};
		for (const p of PILLARS) {
			byPillarAsset[p] = {};
			for (const a of assets) byPillarAsset[p][a] = 0;
		}
		for (const adj of adjustments) {
			if (adj.regime === regime) {
				if (!byPillarAsset[adj.pillar]) byPillarAsset[adj.pillar] = {};
				byPillarAsset[adj.pillar][adj.asset] = adj.delta;
			}
		}

		const rows = PILLARS.map((p) => ({ pillar: p, ...byPillarAsset[p] }));

		const columns: ColumnsType<(typeof rows)[0]> = [
			{ title: "Pillar", dataIndex: "pillar", key: "pillar", width: 100 },
			...assets.map((asset) => ({
				title: asset,
				key: asset,
				width: 110,
				render: (_: unknown, row: (typeof rows)[0]) => {
					const v: number = (row as any)[asset] ?? 0;
					const color =
						v > 0 ? "text-green-600" : v < 0 ? "text-red-500" : "text-gray-400";
					return (
						<span className={`font-mono text-xs ${color}`}>
							{v !== 0 ? `${v > 0 ? "+" : ""}${(v * 100).toFixed(0)}%` : "—"}
						</span>
					);
				},
			})),
			{
				title: "Σ delta",
				key: "sum",
				width: 80,
				render: (_: unknown, row: (typeof rows)[0]) => {
					const sum = assets.reduce(
						(acc, a) => acc + ((row as any)[a] ?? 0),
						0
					);
					const color =
						Math.abs(sum) < 0.001
							? "text-gray-400"
							: "text-amber-600 font-semibold";
					return (
						<span className={`font-mono text-xs ${color}`}>
							{sum > 0 ? "+" : ""}
							{(sum * 100).toFixed(0)}%
						</span>
					);
				},
			},
		];

		return {
			key: regime,
			label: regime.charAt(0).toUpperCase() + regime.slice(1),
			children: (
				<Table
					rowKey="pillar"
					size="small"
					columns={columns}
					dataSource={rows}
					pagination={false}
				/>
			),
		};
	});

	return (
		<Card size="small" title="Allocation adjustments by regime">
			<Tabs size="small" items={tabItems} />
		</Card>
	);
};

export default RegimeAdjustmentsCard;
