import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fmt, roundCurrency, toCents, fromCents } from '../frontend/src/lib/format.js';

test('VND groups thousands in threes and omits zero fractional digits', () => {
  assert.equal(fmt(100000000, 'VND', {}, {}), 'VND 100,000,000');
  assert.equal(fmt(1234567890, 'VND', {}, {}), 'VND 1,234,567,890');
  assert.equal(fmt(0, 'VND', {}, {}), 'VND 0');
});

test('VND retains actual fractional balances', () => {
  assert.equal(fmt(1234567.89, 'VND', {}, {}), 'VND 1,234,567.89');
  assert.equal(fmt(1234567.5, 'VND', {}, {}), 'VND 1,234,567.5');
});

test('Other currencies retain two decimal places with three-digit grouping', () => {
  assert.equal(fmt(100000000, 'USD', {}, {}), 'USD 100,000,000.00');
  assert.equal(fmt(1234567.89, 'EUR', {}, {}), 'EUR 1,234,567.89');
});

test('Configured symbols and symbol position are preserved', () => {
  assert.equal(fmt(100000000, 'VND', { VND: '₫' }, { VND: 1 }), '100,000,000 ₫');
  assert.equal(fmt(1234567.89, 'USD', { USD: '$' }, {}), '$ 1,234,567.89');
});

test('Formatting still leaves sign handling to existing payment and invoice callers', () => {
  assert.equal(fmt(-1234567.89, 'USD', {}, {}), 'USD 1,234,567.89');
  assert.equal(fmt(Number.NaN, 'VND', {}, {}), 'VND 0');
});

test('Display formatting does not change amount conversion or rounding', () => {
  const amount = 1234567.89;
  fmt(amount, 'VND', {}, {});
  assert.equal(roundCurrency(amount), 1234567.89);
  assert.equal(toCents(amount), 123456789);
  assert.equal(fromCents(123456789), amount);
});
