from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_default_pdf_report_id(self, move):
        journal = move.journal_id
        if journal.l10n_ar_is_pos:
            if journal.l10n_ar_afip_pos_system == 'II_IM':
                report = self.env.ref(
                    'custom_invoice_ticket.action_report_invoice_ticket',
                    raise_if_not_found=False,
                )
            else:
                report = self.env.ref(
                    'custom_invoice_ticket.action_report_invoice_ticket_b',
                    raise_if_not_found=False,
                )
            if report and move._is_action_report_available(report):
                return report
        return super()._get_default_pdf_report_id(move)
