from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    can_switch_to_electronic_journal = fields.Boolean(
        compute='_compute_can_switch_to_electronic_journal',
        help="Whether this invoice can be switched from a preprinted journal to an electronic journal.",
    )

    @api.depends(
        'move_type', 'state',
        'journal_id.l10n_ar_is_pos',
        'journal_id.l10n_ar_afip_pos_system',
        'pos_order_ids',
    )
    def _compute_can_switch_to_electronic_journal(self):
        for move in self:
            move.can_switch_to_electronic_journal = (
                move.move_type in ('out_invoice', 'out_refund')
                and move.state in ('draft', 'posted')
                and bool(move.pos_order_ids)
                and move.journal_id.l10n_ar_is_pos
                and move.journal_id.l10n_ar_afip_pos_system == 'II_IM'
            )

    def action_switch_to_electronic_journal(self):
        self.ensure_one()
        if not self.can_switch_to_electronic_journal:
            raise UserError(_("This invoice cannot be switched to an electronic journal."))
        return {
            'name': _('Change to Electronic Journal'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.journal.auto.switch.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }
