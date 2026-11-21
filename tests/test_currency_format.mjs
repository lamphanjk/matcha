import assert from 'node:assert/strict';
import { test, beforeEach } from 'node:test';
import { fmt, roundCurrency, toCents, fromCents } from '../frontend/src/lib/format.js';
import { configureMoneyFormatting } from '../frontend/src/lib/money-format.js';

const standard = {
  number_format: '#,###.##', decimal_separator: '.', group_separator: ',',
  precision: 2, rounding_method: "Banker's Rounding (legacy)",
};
beforeEach(() => configureMoneyFormatting());

test('VND and USD use the same default precision without currency-specific rules', () => {
  assert.equal(fmt(100000000, 'VND', {}, {}), 'VND 100,000,000.00');
  assert.equal(fmt(100000000, 'USD', {}, {}), 'USD 100,000,000.00');
});

test('Site precision zero applies to every currency', () => {
  configureMoneyFormatting({ default: { ...standard, precision: 0 } });
  assert.equal(fmt(100000000, 'VND', {}, {}), 'VND 100,000,000');
  assert.equal(fmt(100000000, 'USD', {}, {}), 'USD 100,000,000');
});

test('Site precision above two retains source fractional digits', () => {
  configureMoneyFormatting({ default: { ...standard, precision: 3 } });
  assert.equal(fmt(1234567.891, 'VND', {}, {}), 'VND 1,234,567.891');
  assert.equal(fmt(1234567, 'USD', {}, {}), 'USD 1,234,567.000');
});

test('Site decimal and group separators are applied', () => {
  configureMoneyFormatting({ default: {
    ...standard, number_format: '#.###,##', decimal_separator: ',', group_separator: '.',
  } });
  assert.equal(fmt(1234567.89, 'VND', {}, {}), 'VND 1.234.567,89');
  assert.equal(fmt(1234567.89, 'USD', {}, {}), 'USD 1.234.567,89');
});

test('Space, apostrophe and multi-character grouping separators work', () => {
  for (const separator of [' ', "'", ', ']) {
    configureMoneyFormatting({ default: { ...standard, group_separator: separator } });
    assert.equal(fmt(1234567.89, 'USD', {}, {}), `USD 1${separator}234${separator}567.89`);
  }
});

test('Indian grouping is used only when configured on the site', () => {
  configureMoneyFormatting({ default: { ...standard, number_format: '#,##,###.##' } });
  assert.equal(fmt(100000000, 'VND', {}, {}), 'VND 10,00,00,000.00');
});

test('Configured number formats with no decimal part omit fractional digits', () => {
  configureMoneyFormatting({ default: {
    ...standard, number_format: '#.###', decimal_separator: '', group_separator: '.', precision: 0,
  } });
  assert.equal(fmt(1234567, 'VND', {}, {}), 'VND 1.234.567');
});

test('Currency overrides supplied by the site apply without hardcoded currency names', () => {
  configureMoneyFormatting({ default: standard, currencies: {
    EUR: { ...standard, decimal_separator: ',', group_separator: '.', number_format: '#.###,##' },
  } });
  assert.equal(fmt(1234567.89, 'EUR', {}, {}), 'EUR 1.234.567,89');
  assert.equal(fmt(1234567.89, 'VND', {}, {}), 'VND 1,234,567.89');
});

test('Configured symbols and symbol position are preserved', () => {
  assert.equal(fmt(100000000, 'VND', { VND: '₫' }, { VND: 1 }), '100,000,000.00 ₫');
  assert.equal(fmt(1234567.89, 'USD', { USD: '$' }, {}), '$ 1,234,567.89');
});

test('Formatting still leaves sign handling to existing callers and handles invalid numbers', () => {
  assert.equal(fmt(-1234567.89, 'USD', {}, {}), 'USD 1,234,567.89');
  assert.equal(fmt(Number.NaN, 'VND', {}, {}), 'VND 0.00');
});

test('Configured display rounding distinguishes half-even and commercial rounding', () => {
  configureMoneyFormatting({ default: { ...standard, precision: 0, rounding_method: "Banker's Rounding" } });
  assert.equal(fmt(2.5, 'VND', {}, {}), 'VND 2');
  configureMoneyFormatting({ default: { ...standard, precision: 0, rounding_method: 'Commercial Rounding' } });
  assert.equal(fmt(2.5, 'VND', {}, {}), 'VND 3');
});

test('Display settings do not change amount conversion or rounding helpers', () => {
  configureMoneyFormatting({ default: { ...standard, precision: 0 } });
  const amount = 1234567.89;
  fmt(amount, 'VND', {}, {});
  assert.equal(roundCurrency(amount), 1234567.89);
  assert.equal(toCents(amount), 123456789);
  assert.equal(fromCents(123456789), amount);
});
