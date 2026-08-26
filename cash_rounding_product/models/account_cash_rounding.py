from odoo import fields, models


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

        rounding_line = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
        if rounding_line and not rounding_line.product_id:
            rounding_line.write({'product_id': rounding_method.product_id.id})
