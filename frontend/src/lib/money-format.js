const fallback = {
  number_format: '#,###.##', decimal_separator: '.', group_separator: ',',
  precision: 2, rounding_method: "Banker's Rounding (legacy)",
};
let defaultFormat = fallback;
let currencyFormats = {};

export function configureMoneyFormatting(settings = {}) {
  defaultFormat = { ...fallback, ...settings.default };
  currencyFormats = settings.currencies || {};
}

export function formatMoneyNumber(value, currency) {
  const config = currencyFormats[currency] || defaultFormat;
  const num = Number(value);
  const precision = config.precision;
  const halfEven = config.rounding_method === "Banker's Rounding"
    || (config.rounding_method === "Banker's Rounding (legacy)" && precision === 0);
  const formatter = new Intl.NumberFormat(config.number_format === '#,##,###.##' ? 'en-IN' : 'en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
    useGrouping: Boolean(config.group_separator),
    roundingMode: halfEven ? 'halfEven' : 'halfExpand',
  });
  return formatter.formatToParts(Number.isFinite(num) ? Math.abs(num) : 0).map(part => {
    if (part.type === 'group') return config.group_separator;
    if (part.type === 'decimal') return config.decimal_separator;
    if (part.type === 'fraction' && !config.decimal_separator) return '';
    return part.value;
  }).join('');
}
