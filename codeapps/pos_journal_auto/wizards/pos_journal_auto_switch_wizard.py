from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Domain


class PosJournalAutoSwitchWizard(models.TransientModel):
    _name = 'pos.journal.auto.switch.wizard'
    _description = 'Change invoice to an electronic journal'

    move_id = fields.Many2one('account.move', string='Invoice', required=True, readonly=True)
    company_id = fields.Many2one('res.company', related='move_id.company_id', readonly=True)
    current_journal_id = fields.Many2one(
        'account.journal', related='move_id.journal_id',
        string='Current journal', readonly=True,
    )
    target_journal_id = fields.Many2one(
        'account.journal',
        string='Electronic journal',
        required=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'sale'), "
               "('l10n_ar_is_pos', '=', True), ('l10n_ar_afip_pos_system', '!=', 'II_IM')]",
        check_company=True,
        help="Journal where the invoice will be re-issued after the preprinted document is voided.",
    )
    new_document_type_id = fields.Many2one(
        'l10n_latam.document.type', compute='_compute_document_types',
        string='New document type',
    )

    @api.depends('target_journal_id', 'move_id')
    def _compute_document_types(self):
        for wizard in self:
            move = wizard.move_id
            journal = wizard.target_journal_id
            wizard.new_document_type_id = False
            if not journal or not move:
                continue
            internal_types = ['invoice', 'debit_note'] if move.move_type == 'out_invoice' else ['credit_note']
            domain = [
                ('internal_type', 'in', internal_types + ['all']),
                ('country_id', '=', move.company_id.country_id.id),
            ]
            if journal.country_code == 'AR':
                if move.company_id.l10n_ar_afip_responsibility_type_id:
                    letters = journal._get_journal_letter(counterpart_partner=move.partner_id.commercial_partner_id)
                    domain = Domain(domain)
                    domain &= Domain('l10n_ar_letter', '=', False) | Domain('l10n_ar_letter', 'in', letters)
                    domain &= Domain(journal._get_journal_codes_domain())
                    if move.move_type == 'out_refund':
                        domain = Domain('code', 'in', move._get_l10n_ar_codes_used_for_inv_and_ref()) | domain
            doc_types = self.env['l10n_latam.document.type'].search(domain)
            wizard.new_document_type_id = doc_types[:1]

    def action_switch_journal(self):
        self.ensure_one()
        move = self.move_id
        target_journal = self.target_journal_id
        if target_journal.id == move.journal_id.id:
            raise UserError(_("The invoice is already in the selected journal."))

        if move.state == 'draft':
            move.write({'journal_id': target_journal.id})
        else:
            order = move.sudo().pos_order_ids
            if not order:
                raise UserError(_("This invoice is not linked to a Point of Sale order."))
            move = order._pos_journal_auto_switch_invoice_journal(move, target_journal)

        return {
            'name': _('Customer Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_id': move.id,
            'target': 'current',
            'context': {'move_type': move.move_type},
        }
