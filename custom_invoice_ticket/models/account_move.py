from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_invoice_download_pdf(self, target="download"):
        if self.journal_id.l10n_ar_is_pos:
            report = self.env['account.move.send']._get_default_pdf_report_id(self)
            if report:
                return report.with_context(
                    skip_invoice_sync=True,
                ).report_action(self.id, config=False)
        return super().action_invoice_download_pdf(target=target)
