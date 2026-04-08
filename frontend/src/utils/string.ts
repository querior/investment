export const capitalize = (s: string | undefined) =>
	s ? s[0].toUpperCase() + s.slice(1) : "";

export const fmt = (
	v: number | null | undefined,
	percent = false,
	decimals = 2
): string => {
	if (v == null) return "—";
	return percent ? `${(v * 100).toFixed(decimals)}%` : v.toFixed(decimals);
};
