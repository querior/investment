import { Card, Statistic } from "antd";
import { useSelector } from "react-redux";
import { RootState } from "../../store/reducers";
import { BacktestRunDto } from "../../features/backtest/types";
import { fmt } from "../../utils/string";

interface MetricsProps {
	currentRun: BacktestRunDto;
}

const Metrics = ({ currentRun }: MetricsProps) => {
	return (
		<div className="grid grid-cols-4 gap-4">
			<Card size="small">
				<Statistic
					title="CAGR"
					value={fmt(currentRun.cagr, true)}
					valueStyle={{
						color: (currentRun.cagr ?? 0) >= 0 ? "#3f8600" : "#cf1322",
					}}
				/>
			</Card>
			<Card size="small">
				<Statistic title="Sharpe Ratio" value={fmt(currentRun.sharpe)} />
			</Card>
			<Card size="small">
				<Statistic
					title="Volatility"
					value={fmt(currentRun.volatility, true)}
				/>
			</Card>
			<Card size="small">
				<Statistic
					title="Max Drawdown"
					value={fmt(currentRun.max_drawdown, true)}
					valueStyle={{ color: "#cf1322" }}
				/>
			</Card>
			<Card size="small">
				<Statistic title="Win Rate" value={fmt(currentRun.win_rate, true)} />
			</Card>
			<Card size="small">
				<Statistic
					title="Profit Factor"
					value={fmt(currentRun.profit_factor)}
				/>
			</Card>
			<Card size="small">
				<Statistic title="N. trade" value={currentRun.n_trades ?? "—"} />
			</Card>
		</div>
	);
};

export default Metrics;
