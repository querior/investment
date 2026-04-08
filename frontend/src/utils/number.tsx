export function formatCurrency(value: number | undefined): string {
	if (value == null) return "—";
	return new Intl.NumberFormat("en-US", {
		style: "currency",
		currency: "USD",
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	}).format(value);
}

export function formatPercent(value: number | undefined): string {
	if (value == null) return "—";
	return `${(value * 100).toFixed(2)}%`;
}

export function formatNumber(value: number | undefined, decimals = 2): string {
	if (value == null) return "—";
	return value.toFixed(decimals);
}

export function formatDelta(value: number | undefined): JSX.Element {
	if (value == null) return <span className="text-gray-400">—</span>;
	const color = value < 0 ? "text-red-500" : "text-green-600";
	return <span className={color}>{value.toFixed(4)}</span>;
}
