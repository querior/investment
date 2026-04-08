import { useSelector } from "react-redux";
import { RootState } from "../../../store/reducers";

type ParamDraft = Record<string, string | number>;

interface StartingAllocationProps {
	draft: ParamDraft | null;
}

const StartingAllocation = ({ draft }: StartingAllocationProps) => {
	const { currentRun, backtestConfig } = useSelector(
		(state: RootState) => state.backtest
	);

	if (!currentRun) return <div>Waiting...</div>;

	return (
		<>
			{currentRun.parameters &&
			(draft?.initial_allocation ??
				currentRun.parameters.initial_allocation) === "neutral" ? (
				backtestConfig && (
					<div className="col-span-2 pt-3 border-t border-gray-100">
						<span className="text-gray-500 text-xs uppercase tracking-wide block mb-2">
							Portafoglio neutro
						</span>
						<div className="flex gap-6">
							{backtestConfig?.neutral &&
								Object.entries(backtestConfig.neutral).map(([asset, w]) => (
									<div key={asset} className="text-sm">
										<span className="font-medium">{asset}</span>
										<div className="font-mono text-gray-700">
											{(w * 100).toFixed(0)}%
										</div>
									</div>
								))}
						</div>
					</div>
				)
			) : (draft?.initial_allocation ??
					currentRun.parameters.initial_allocation) !== "neutral" ? (
				<div className="col-span-2 pt-3 border-t border-gray-100">
					<span className="text-gray-400 text-xs">
						L'allocazione iniziale sarà il target calcolato al primo mese
						disponibile. Visibile dopo l'esecuzione.
					</span>
				</div>
			) : null}
		</>
	);
};

export default StartingAllocation;
