import logging

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)


class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Rounding Product',
        domain="[('type', '=', 'service')]",
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_cash_rounding_lines(self):
        super()._recompute_cash_rounding_lines()

        rounding_method = self.invoice_cash_rounding_id
        if not rounding_method or not rounding_method.product_id:
            return

        rounding_lines = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
        for rl in rounding_lines:
            vals = {}
            if not rl.product_id:
                vals['product_id'] = rounding_method.product_id.id
            if rl.tax_ids:
                vals['tax_ids'] = [Command.clear()]
            if vals:
                rl.with_context(skip_invoice_sync=True).write(vals)
