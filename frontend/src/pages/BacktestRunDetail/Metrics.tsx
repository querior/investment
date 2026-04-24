import { Card, Statistic } from "antd";
import { useSelector } from "react-redux";
import { RootState } from "../../store/reducers";
import { BacktestRunDto } from "../../features/backtest/types";
import { fmt } from "../../utils/string";

interface MetricsProps {
	currentRun: BacktestRunDto;
}

const Metrics = ({ currentRun }: MetricsProps) => {
	// Use summary object if available, otherwise fallback to top-level fields
	const summary = currentRun.summary || currentRun;

	return (
		<div className="grid grid-cols-4 gap-4">
			<Card size="small">
				<Statistic
					title="CAGR"
					value={fmt(summary.cagr, true)}
					valueStyle={{
						color: (summary.cagr ?? 0) >= 0 ? "#3f8600" : "#cf1322",
					}}
				/>
			</Card>
			<Card size="small">
				<Statistic title="Sharpe Ratio" value={fmt(summary.sharpe)} />
			</Card>
			<Card size="small">
				<Statistic
					title="Volatility"
					value={fmt(summary.volatility, true)}
				/>
			</Card>
			<Card size="small">
				<Statistic
					title="Max Drawdown"
					value={fmt(summary.max_drawdown, true)}
					valueStyle={{ color: "#cf1322" }}
				/>
			</Card>
			<Card size="small">
				<Statistic title="Win Rate" value={fmt(summary.win_rate, true)} />
			</Card>
			<Card size="small">
				<Statistic
					title="Profit Factor"
					value={fmt(summary.profit_factor)}
				/>
			</Card>
			<Card size="small">
				<Statistic title="N. trade" value={summary.n_trades ?? "—"} />
			</Card>
		</div>
	);
};

export default Metrics;
