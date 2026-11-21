import { useEffect, useState } from 'react';
import { useAppStore } from '../store';
import { apiCall, parseServerMessage } from '../lib/api';
import { fmt } from '../lib/format';
import { getDatesForFilter } from '../lib/dates';

export default function PartySummary() {
  const { currentCompany, partyFilter, dateFilter, customFromDate, customToDate,
    currencySymbols, currencySymbolOnRight, invoices, payments } = useAppStore();
  const [partyType, setPartyType] = useState('Customer');
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState([]);
  const [chosen, setChosen] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const party = chosen || partyFilter;

  useEffect(() => { setChosen(null); setQuery(''); setOptions([]); }, [currentCompany]);
  useEffect(() => { if (partyFilter?.party) setChosen(partyFilter); }, [partyFilter]);

  useEffect(() => {
    let cancelled = false;
    setOptions([]);
    if (!query.trim()) return;
    const timer = setTimeout(() => {
      apiCall('matcha.api.party_summary.search_parties', { party_type: partyType, search: query })
        .then(res => {
          if (cancelled) return;
          if (res.exc) throw new Error(parseServerMessage(res, 'Unable to find parties'));
          setOptions(res.message || []);
        }).catch(e => { if (!cancelled) setError(e.message); });
    }, 300);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, partyType]);

  useEffect(() => {
    let cancelled = false;
    setResult(null); setError(''); setLoading(false);
    if (!currentCompany || !party?.party || !['Customer', 'Supplier'].includes(party.party_type)) return;
    setLoading(true);
    apiCall('matcha.api.party_summary.get_party_summary', {
      company: currentCompany, party_type: party.party_type, party: party.party,
      ...getDatesForFilter(dateFilter, customFromDate, customToDate),
    }).then(res => {
      if (cancelled) return;
      if (res.exc) throw new Error(parseServerMessage(res, 'Unable to load party balances'));
      setResult(res.message || { totals: [] }); setLoading(false);
    }).catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [currentCompany, party?.party, party?.party_type, dateFilter, customFromDate, customToDate, invoices, payments]);

  return <section className="party-summary" aria-label="Party balances">
    <strong>Party balances</strong>
    <div className="party-summary-search">
      <select aria-label="Party type" value={partyType} onChange={e => {
        setPartyType(e.target.value); setChosen(null); setQuery(''); setOptions([]);
      }}><option>Customer</option><option>Supplier</option></select>
      <input aria-label="Find party for balances" placeholder="Find party by name…" value={query}
        onChange={e => { setQuery(e.target.value); setError(''); }} />
    </div>
    {options.length > 0 && <div className="party-summary-options">
      {options.map(option => <button type="button" key={option.name} onClick={() => {
        setChosen({ party_type: partyType, party: option.name }); setQuery(''); setOptions([]);
      }}>{option.label} · {option.name}</button>)}
    </div>}
    {party?.party && <div className="party-summary-name">{party.party_type}: {party.party}
      {chosen && <button type="button" className="btn btn-sm" onClick={() => setChosen(null)}>Clear</button>}
    </div>}
    {loading && <p role="status">Loading balances…</p>}
    {error && <p role="alert">{error}</p>}
    {result?.totals?.map(total => <div className="sum-cards" key={total.currency}>
      {['billing', 'paid', 'unpaid'].map(key => <div className="sum-card" key={key}>
        <div className="sum-card-val">{fmt(total[key], total.currency, currencySymbols, currencySymbolOnRight)}</div>
        <div className="sum-card-label">Total {key}{key === 'paid' ? ' / adjusted' : ''}</div>
      </div>)}
    </div>)}
    {result && !result.totals.length && <p>No submitted invoices in this date range.</p>}
    <small>Posting dates use the top date filter. Balances are current; paid includes adjustments. Unallocated payments are excluded.</small>
  </section>;
}
