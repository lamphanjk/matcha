frappe.ui.form.on('Matcha Settings', {
	refresh(frm) {
		render_invoice_fields(frm);
	},
	onload(frm) {
		frm.set_query('intercompany_account', 'intercompany_accounts', (doc, cdt, cdn) => {
			const row = frappe.get_doc(cdt, cdn);
			return {
				filters: {
					company: row.company || '',
					is_group: 0,
				},
			};
		});
	},
});

frappe.ui.form.on('Matcha Intercompany Account', {
	company(frm, cdt, cdn) {
		// Clear stale account selection when company changes
		frappe.model.set_value(cdt, cdn, 'intercompany_account', '');
	},
});


async function render_invoice_fields(frm) {
    const wrapper = frm.fields_dict.invoice_fields_editor.$wrapper;
    wrapper.empty();
    const config = JSON.parse(frm.doc.invoice_field_config || '{}');
    wrapper.append($('<p>').text(__('Choose fields from each invoice type, including custom fields. Display and filter choices are independent. Save settings, then refresh Matcha.')));
    for (const doctype of ['Sales Invoice', 'Purchase Invoice']) {
        const section = $('<div class="mb-4">').appendTo(wrapper);
        $('<h5>').text(__(doctype)).appendTo(section);
        if (!frappe.model.can_read(doctype)) {
            $('<p>').text(__('No read permission')).appendTo(section);
            continue;
        }
        const response = await frappe.call({method: 'matcha.api.invoice_fields.get_invoice_fields', args: {doctype}});
        const fields = response.message || [];
        const valid = new Set(fields.map(field => field.fieldname));
        for (const key of ['display', 'filter']) {
            const selected = config[doctype]?.[key] || [];
            const current = selected.filter(name => valid.has(name));
            if (current.length !== selected.length) {
                config[doctype][key] = current;
                frm.set_value('invoice_field_config', JSON.stringify(config));
            }
        }
        const search = $('<input type="search" class="form-control mb-2">').attr('placeholder', __('Find field by label or fieldname')).appendTo(section);
        const table = $('<table class="table table-bordered">').appendTo(section);
        const head = $('<tr>').appendTo($('<thead>').appendTo(table));
        [__('Field'), __('Display'), __('Filter')].forEach(label => $('<th>').text(label).appendTo(head));
        const body = $('<tbody>').appendTo(table);
        fields.forEach(field => {
            const row = $('<tr>').appendTo(body);
            $('<td>').text(`${field.label} (${field.fieldname})`).appendTo(row);
            ['display', 'filter'].forEach(key => {
                const cell = $('<td>').appendTo(row);
                $('<input type="checkbox">').attr('aria-label', `${field.label}: ${key}`)
                    .prop('checked', (config[doctype]?.[key] || []).includes(field.fieldname))
                    .prop('disabled', !frm.perm[0]?.write)
                    .appendTo(cell).on('change', function () {
                        config[doctype] ||= {display: [], filter: []};
                        const selected = new Set(config[doctype][key] || []);
                        if (this.checked) selected.add(field.fieldname);
                        else selected.delete(field.fieldname);
                        config[doctype][key] = [...selected];
                        frm.set_value('invoice_field_config', JSON.stringify(config));
                    });
            });
        });
        search.on('input', () => {
            const term = search.val().toLowerCase();
            body.children().each(function () { $(this).toggle($(this).text().toLowerCase().includes(term)); });
        });
    }
}
