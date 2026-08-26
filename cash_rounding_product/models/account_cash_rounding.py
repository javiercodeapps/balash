from odoo import Command, fields, models
from odoo.tools import float_compare


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
        rounding_method = self.invoice_cash_rounding_id

        if rounding_method and rounding_method.product_id:
            self._recompute_cash_rounding_with_product(rounding_method)
            return

        super()._recompute_cash_rounding_lines()

    def _recompute_cash_rounding_with_product(self, rounding_method):
        self.ensure_one()

        self.line_ids.filtered(lambda line: line.display_type == 'rounding').unlink()

        existing_product_line = self.line_ids.filtered(
            lambda line: line.display_type == 'product'
            and line.product_id == rounding_method.product_id
        )

        if not self.invoice_cash_rounding_id:
            existing_product_line.unlink()
            return

        others_lines = self.line_ids.filtered(
            lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable')
            and line.display_type == 'product'
            and (not rounding_method.product_id or line.product_id != rounding_method.product_id)
        )
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        difference = rounding_method.compute_difference(self.currency_id, total_amount_currency)
        if self.currency_id == self.company_id.currency_id:
            diff_amount_currency = diff_balance = difference
        else:
            diff_amount_currency = difference
            diff_balance = self.currency_id._convert(
                diff_amount_currency, self.company_id.currency_id,
                self.company_id, self.invoice_date or self.date,
            )

        if self.currency_id.is_zero(diff_amount_currency):
            existing_product_line.unlink()
            return

        if existing_product_line \
            and float_compare(existing_product_line.amount_currency, diff_amount_currency, precision_rounding=self.currency_id.rounding) == 0:
            return

        product = rounding_method.product_id
        taxes = product.taxes_id
        total_tax_rate = sum(taxes.mapped('amount')) / 100.0 if taxes else 0.0

        if total_tax_rate > 0:
            base_amount = diff_amount_currency / (1.0 + total_tax_rate)
            base_balance = diff_balance / (1.0 + total_tax_rate)
        else:
            base_amount = diff_amount_currency
            base_balance = diff_balance

        if diff_balance > 0.0 and rounding_method.loss_account_id:
            account_id = rounding_method.loss_account_id.id
        else:
            account_id = rounding_method.profit_account_id.id

        line_vals = {
            'name': product.name,
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'tax_ids': [Command.set(taxes.ids)],
            'amount_currency': base_amount,
            'balance': base_balance,
            'account_id': account_id,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'display_type': 'product',
        }

        if existing_product_line:
            existing_product_line.with_context(skip_invoice_sync=True).write(line_vals)
        else:
            self.env['account.move.line'].with_context(skip_invoice_sync=True).create({
                **line_vals,
                'move_id': self.id,
            })
