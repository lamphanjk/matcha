import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const script = readFileSync(new URL('../matcha/matcha/doctype/matcha_settings/matcha_settings.js', import.meta.url), 'utf8');

class Element {
  constructor(html) { this.html = html; this.nodes = []; this.value = ''; }
  empty() { this.nodes = []; return this; }
  append(child) { this.nodes.push(child); return this; }
  appendTo(parent) { parent.append(this); return this; }
  text(value) { this.value = value; return this; }
  attr() { return this; }
  prop() { return this; }
  on() { return this; }
  allText() { return [this.value, ...this.nodes.map(child => child.allText())].join(' '); }
}

function settings(call, config = '{}') {
  const handlers = {};
  const requests = [];
  const writes = [];
  const wrapper = new Element('root');
  const context = vm.createContext({
    $: html => new Element(html),
    __: text => text,
    frappe: {
      ui: { form: { on: (doctype, events) => { handlers[doctype] = events; } } },
      model: { can_read: () => true },
      call: async options => {
        requests.push(options);
        // Frappe v15 defaults to POST. The metadata API permits GET only.
        if ((options.type || 'POST') !== 'GET') throw new Error('403: invalid HTTP method');
        return call(options);
      },
    },
  });
  vm.runInContext(script, context);
  const frm = {
    doc: { invoice_field_config: config }, perm: [{ write: true }],
    fields_dict: { invoice_fields_editor: { $wrapper: wrapper } },
    set_value: (...args) => writes.push(args),
  };
  return { refresh: () => handlers['Matcha Settings'].refresh(frm), requests, writes, wrapper };
}

test('Settings loads custom field metadata for both invoice types with GET', async () => {
  const form = settings(() => ({ message: [
    { fieldname: 'custom_contract', label: 'Contract', fieldtype: 'Data' },
  ] }));
  await form.refresh();
  assert.deepEqual(form.requests.map(request => request.type), ['GET', 'GET']);
  assert.deepEqual(form.requests.map(request => request.args.doctype), ['Sales Invoice', 'Purchase Invoice']);
  assert.match(form.wrapper.allText(), /Contract \(custom_contract\)/);
  assert.equal(form.writes.length, 0);
});

test('A rejected invoice metadata request does not abort the other type or clear saved selections', async () => {
  const form = settings(options => {
    if (options.args.doctype === 'Sales Invoice') throw new Error('403: no read permission');
    return { message: [{ fieldname: 'supplier', label: 'Supplier' }] };
  }, JSON.stringify({ 'Sales Invoice': { display: ['custom_contract'], filter: [] } }));
  await assert.doesNotReject(form.refresh());
  assert.equal(form.requests.length, 2);
  assert.match(form.wrapper.allText(), /Unable to load fields for this invoice type/);
  assert.match(form.wrapper.allText(), /Supplier \(supplier\)/);
  assert.equal(form.writes.length, 0);
});

test('Malformed saved settings render an error without an unhandled rejection or writes', async () => {
  const form = settings(() => ({ message: [] }), '{invalid json');
  await assert.doesNotReject(form.refresh());
  assert.match(form.wrapper.allText(), /Unable to load invoice field settings/);
  assert.equal(form.requests.length, 0);
  assert.equal(form.writes.length, 0);
});
