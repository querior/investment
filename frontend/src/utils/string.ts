export const capitalize = (s: string | undefined) =>
	s ? s[0].toUpperCase() + s.slice(1) : "";
