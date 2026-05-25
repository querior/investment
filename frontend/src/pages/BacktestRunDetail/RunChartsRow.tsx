import { Card } from "antd";
import { useSelector } from "react-redux";
import type { RootState } from "../../store/reducers";
import MarketContextChart from "../../components/charts/MarketContextChart";
import PnlAttributionChart from "../../components/charts/PnlAttributionChart";

export default function RunChartsRow() {
	const { currentRun } = useSelector((state: RootState) => state.backtest);

	const ts = currentRun?.portfolio_timeseries ?? [];
	const ticker = currentRun?.parameters?.ticker?.value ?? "Underlying";

	const equityData = ts.map((d) => ({
		date: new Date(d.snapshot_date),
		value: d.total_equity,
	}));
	const underlyingData = ts.map((d) => ({
		date: new Date(d.snapshot_date),
		value: d.underlying_price,
	}));
	const ivData = ts.map((d) => ({
		date: new Date(d.snapshot_date),
		value: d.iv * 100,
	}));
	const realizedData = ts.map((d) => ({
		date: new Date(d.snapshot_date),
		value: d.realized_pnl,
	}));
	const unrealizedData = ts.map((d) => ({
		date: new Date(d.snapshot_date),
		value: d.unrealized_pnl,
	}));

	if (!ts.length) return null;

	return (
		<div className="flex gap-4">
			<Card size="small" title="Market Context" className="flex-1 min-w-0">
				<MarketContextChart
					equityData={equityData}
					priceData={underlyingData}
					ivData={ivData}
					ticker={ticker}
				/>
			</Card>
			<Card size="small" title="P&L Attribution" className="flex-1 min-w-0">
				<PnlAttributionChart
					realizedData={realizedData}
					unrealizedData={unrealizedData}
				/>
			</Card>
		</div>
	);
}
