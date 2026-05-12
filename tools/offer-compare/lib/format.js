export const fmtUSD = (v, opts = {}) => {
  if (v == null || isNaN(v)) return "—";
  const { compact = false, fractionDigits = 0 } = opts;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits
  }).format(v);
};

export const fmtPct = (v, digits = 1) => {
  if (v == null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
};

export const fmtNumber = (v, digits = 0) => {
  if (v == null || isNaN(v)) return "—";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(v);
};

export const parseMoney = (str) => {
  if (str == null || str === "") return 0;
  const cleaned = String(str).replace(/[$,\s]/g, "");
  const n = Number(cleaned);
  return isFinite(n) ? n : 0;
};
