from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    invoice_can_switch_to_electronic_journal = fields.Boolean(
        compute='_compute_invoice_can_switch_to_electronic_journal',
        compute_sudo=True,
        help="Whether the invoice of this order is in a preprinted journal and can be "
             "switched to an electronic journal. Sent to the POS frontend.",
    )

    @api.depends('account_move.can_switch_to_electronic_journal')
    def _compute_invoice_can_switch_to_electronic_journal(self):
        for order in self:
            order.invoice_can_switch_to_electronic_journal = (
                order.account_move.can_switch_to_electronic_journal
            )

    def _get_invoice_journal_id(self):
        """Return the journal to be used when generating the invoice for this order.

        Priority:
        1. a billing journal forced through the context (used by the switch-to-electronic wizard);
        2. the billing journal assigned to the payment method(s) used in the order (exactly one);
        3. the invoice journal configured on the POS config.
        """
        journal_id = self.env.context.get('pos_journal_auto_invoice_journal_id')
        if journal_id:
            return self.env['account.journal'].browse(journal_id)
        billing_journals = self.mapped('payment_ids.payment_method_id').invoice_journal_id.filtered('active')
        if len(billing_journals) == 1:
            return billing_journals
        return self[:1].config_id.invoice_journal_id

    def _prepare_invoice_vals(self):
        invoice_vals = super()._prepare_invoice_vals()
        journal = self._get_invoice_journal_id()
        if journal:
            invoice_vals['journal_id'] = journal.id
        return invoice_vals

    def _pos_journal_auto_switch_invoice_journal(self, invoice, target_journal):
        """Void a preprinted invoice and re-issue it in the electronic journal.

        The invoice never participates in the session closing reconciliations (those
        happen between the payment moves and the closing entry on the POS receivable
        account), so voiding + re-issuing is safe whether the session is open or closed.
        Odoo only allows resetting a POS invoice to draft once the session is closed,
        so while the session is still open the void is done at a lower level.
        """
        self.ensure_one()
        if invoice.state == 'posted':
            if any(session.state != 'closed' for session in self.session_id):
                invoice.line_ids.remove_move_reconcile()
                invoice.write({'auto_post': 'no', 'state': 'cancel'})
            else:
                invoice.button_cancel()
        invoice.message_post(body=_(
            "Invoice voided because it was re-issued in the electronic journal %s",
            target_journal.display_name,
        ))

        invoice_vals = self.with_context(
            pos_journal_auto_invoice_journal_id=target_journal.id
        )._prepare_invoice_vals()
        new_invoice = self._create_invoice(invoice_vals)
        new_invoice.sudo().with_company(self.company_id).with_context(
            skip_invoice_sync=True
        )._post()

        payment_moves = self.sudo().payment_ids.account_move_id
        self._reconcile_invoice_payments(new_invoice, payment_moves)
        new_invoice.message_post(body=_(
            "Invoice re-issued in the electronic journal %s, replacing the voided "
            "preprinted invoice %s.",
            target_journal.display_name,
            invoice.name,
        ))
        return new_invoice

    def _get_electronic_invoice_journals(self):
        """Return the electronic (non preprinted) sale journals of the order company."""
        self.ensure_one()
        return self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('type', '=', 'sale'),
            ('l10n_ar_is_pos', '=', True),
            ('l10n_ar_afip_pos_system', '!=', 'II_IM'),
        ])

    def action_pos_journal_auto_get_electronic_journals(self):
        """Return the electronic journals available to switch the invoice of this order."""
        self.ensure_one()
        return [(journal.id, journal.name) for journal in self.sudo()._get_electronic_invoice_journals()]

    def action_pos_journal_auto_switch_invoice(self, target_journal_id):
        """Switch the invoice of this order to an electronic journal (called from the POS)."""
        self.ensure_one()
        order = self.sudo()
        invoice = order.account_move
        if not invoice or not invoice.can_switch_to_electronic_journal:
            raise UserError(_("The invoice of this order cannot be switched to an electronic journal."))
        target_journal = self.env['account.journal'].browse(target_journal_id)
        if not target_journal or target_journal not in order._get_electronic_invoice_journals():
            raise UserError(_("The selected journal is not a valid electronic journal for this order."))
        if target_journal.id == invoice.journal_id.id:
            raise UserError(_("The invoice is already in the selected journal."))
        new_invoice = order._pos_journal_auto_switch_invoice_journal(invoice, target_journal)
        return {
            'new_invoice_id': new_invoice.id,
            'new_invoice_name': new_invoice.name,
            'old_invoice_name': invoice.name,
        }
