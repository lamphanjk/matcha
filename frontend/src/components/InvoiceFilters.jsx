import { useEffect, useState } from 'react';
import { apiCall, parseServerMessage } from '../lib/api';
import { useAppStore } from '../store';

const numericTypes = ['Currency', 'Float', 'Int', 'Long Int', 'Percent'];
const textTypes = ['Data', 'Link', 'Dynamic Link', 'Select', 'Small Text', 'Text'];

export default function InvoiceFilters() {
  const { exceptionsInvoiceStatus, setExceptionsInvoiceStatus, exceptionsInvoiceFilters,
    setExceptionsInvoiceFilters, exceptionsParty, toast } = useAppStore();
  const [config, setConfig] = useState({});
  const [fieldKey, setFieldKey] = useState('');
  const [operator, setOperator] = useState('=');
  const [value, setValue] = useState('');

  useEffect(() => {
    let cancelled = false;
    apiCall('matcha.api.invoice_fields.get_configuration').then(res => {
      if (cancelled) return;
      if (res.exc) throw new Error(parseServerMessage(res, 'Unable to load invoice fields'));
      setConfig(res.message || {});
    }).catch(error => { if (!cancelled) toast(error.message); });
    return () => { cancelled = true; };
  }, [toast]);

  const partyInvoiceType = exceptionsParty?.party_type === 'Customer' ? 'Sales Invoice' : 'Purchase Invoice';
  const fields = Object.entries(config).filter(([doctype]) => !exceptionsParty || doctype === partyInvoiceType)
    .flatMap(([doctype, selection]) =>
    (selection.filter || []).map(field => ({ ...field, doctype, key: `${doctype}:${field.fieldname}` })));
  const field = fields.find(f => f.key === fieldKey);
  const isNumber = numericTypes.includes(field?.fieldtype);
  const operators = [['=', '='], ['!=', '≠'], ...(textTypes.includes(field?.fieldtype)
    ? [['like', 'Contains']] : [['>', '>'], ['>=', '≥'], ['<', '<'], ['<=', '≤']])];

  function addFilter() {
    if (!field || value === '') return;
    const filterValue = isNumber || field.fieldtype === 'Check' ? Number(value) : value;
    setExceptionsInvoiceFilters([...exceptionsInvoiceFilters,
      [field.doctype, field.fieldname, operator, operator === 'like' ? `%${value}%` : filterValue]]);
    setValue('');
  }

  return (
    <div className="invoice-filters" aria-label="Invoice filters">
      <strong>Invoice filters</strong>
      <label>Status <select value={exceptionsInvoiceStatus} onChange={e => setExceptionsInvoiceStatus(e.target.value)}>
        <option value="ageing">Ageing open invoices (30+ days)</option>
        <option value="open">All open invoices</option>
        <option value="paid">Paid / settled invoices</option>
        <option value="all">All submitted invoices</option>
      </select></label>
      {fields.length > 0 && <div className="invoice-filter-builder">
        <select aria-label="Invoice field" value={fieldKey} onChange={e => {
          setFieldKey(e.target.value); setOperator('='); setValue('');
        }}>
          <option value="">Select invoice field…</option>
          {fields.map(f => <option key={f.key} value={f.key}>{f.doctype}: {f.label}</option>)}
        </select>
        <select aria-label="Filter operator" value={operator} onChange={e => setOperator(e.target.value)}>
          {operators.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
        {['Select', 'Check'].includes(field?.fieldtype) ? (
          <select aria-label="Filter value" value={value} onChange={e => setValue(e.target.value)}>
            <option value="">Select value…</option>
            {(field.fieldtype === 'Check' ? ['0', '1'] : (field.options || '').split('\n').filter(Boolean))
              .map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        ) : <input aria-label="Filter value" value={value} onChange={e => setValue(e.target.value)}
          type={isNumber ? 'number' : field?.fieldtype === 'Date' ? 'date' : field?.fieldtype === 'Datetime'
            ? 'datetime-local' : field?.fieldtype === 'Time' ? 'time' : 'text'} step="any" />}
        <button type="button" className="btn btn-sm" disabled={!field || value === '' || exceptionsInvoiceFilters.length >= 30}
          onClick={addFilter}>Add filter</button>
      </div>}
      <div className="invoice-filter-chips">
        {exceptionsInvoiceFilters.map(([doctype, name, op, val], index) => (
          <button type="button" className="btn btn-sm" key={index} title="Remove filter"
            onClick={() => setExceptionsInvoiceFilters(exceptionsInvoiceFilters.filter((_, i) => i !== index))}>
            {doctype}: {fields.find(f => f.doctype === doctype && f.fieldname === name)?.label || name} {op} {val} ×
          </button>
        ))}
        {exceptionsInvoiceFilters.length > 0 && <button type="button" className="btn btn-sm"
          onClick={() => setExceptionsInvoiceFilters([])}>Clear field filters</button>}
      </div>
      <small>Apply only to invoices for the selected party. Payments are unchanged. Fields on the same invoice type use AND.</small>
    </div>
  );
}
