import { useEffect, useState } from 'react';
import { apiCall, parseServerMessage } from '../lib/api';
import { useAppStore } from '../store';

export default function ExceptionPartyFilter() {
  const { exceptionsParty, setExceptionsParty, setExceptionsInvoiceFilters } = useAppStore();
  const [partyType, setPartyType] = useState(exceptionsParty?.party_type || 'Customer');
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setOptions([]); setError(''); setLoading(false);
    if (!query.trim()) return;
    setLoading(true);
    const timer = setTimeout(() => {
      apiCall('matcha.api.party_summary.search_parties', { party_type: partyType, search: query })
        .then(res => {
          if (cancelled) return;
          if (res.exc) throw new Error(parseServerMessage(res, 'Unable to find parties'));
          setOptions(res.message || []); setLoading(false);
        }).catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [partyType, query]);

  return <div className="exception-party-filter">
    <strong>Party — Payments &amp; Invoices</strong>
    <div className="party-summary-search">
      <select aria-label="Exceptions party type" value={partyType} onChange={e => {
        setPartyType(e.target.value); setQuery('');
      }}><option>Customer</option><option>Supplier</option></select>
      <input aria-label="Find exceptions party" placeholder="Search party name or ID…"
        value={query} onChange={e => setQuery(e.target.value)} />
    </div>
    {loading && <small role="status">Finding parties…</small>}
    {error && <small role="alert">{error}</small>}
    {!loading && !error && query.trim() && !options.length && <small>No parties found.</small>}
    {options.length > 0 && <div className="party-summary-options">
      {options.map(option => <button type="button" key={option.name} onClick={() => {
        const invoiceType = partyType === 'Customer' ? 'Sales Invoice' : 'Purchase Invoice';
        setExceptionsInvoiceFilters(filters => filters.filter(([doctype]) => doctype === invoiceType));
        setExceptionsParty({ party_type: partyType, party: option.name, label: option.label });
        setQuery(''); setOptions([]);
      }}>{option.label} · {option.name}</button>)}
    </div>}
    {exceptionsParty ? <div className="exception-party-selection">
      <span>{exceptionsParty.party_type}: {exceptionsParty.label || exceptionsParty.party}
        {exceptionsParty.label && exceptionsParty.label !== exceptionsParty.party && <> · {exceptionsParty.party}</>}
      </span>
      <button type="button" className="btn btn-sm" onClick={() => {
        setExceptionsParty(null); setQuery('');
      }}>Clear party</button>
    </div> : <small>All parties. Select a search result to filter both lists.</small>}
    {exceptionsParty && <small>This party applies to both lists, even when no unmatched payment exists.</small>}
  </div>;
}
