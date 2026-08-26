import logging

from odoo import Command, fields, models
from odoo.tools import float_round

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

            if vals:
                rl.with_context(skip_invoice_sync=True).write(vals)

            if rl.product_id and rl.tax_ids:
                total_tax_rate = sum(rl.tax_ids.mapped('amount')) / 100.0
                if total_tax_rate > 0:
                    base_amount = rl.amount_currency / (1.0 + total_tax_rate)
                    rl.with_context(skip_invoice_sync=True).write({
                        'amount_currency': base_amount,
                        'balance': base_amount,
                    })
