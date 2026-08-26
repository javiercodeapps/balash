from odoo import Command, fields, models, _
from odoo.tools import float_compare


class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Rounding Product',
        domain="[('type', '=', 'service')]",
        help='Product used for the rounding line on invoices. '
             'If set, the rounding line will use this product instead of just the rounding name.',
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_cash_rounding_lines(self):
        self.ensure_one()

        def _compute_cash_rounding(self, total_amount_currency):
            difference = self.invoice_cash_rounding_id.compute_difference(self.currency_id, total_amount_currency)
            if self.currency_id == self.company_id.currency_id:
                diff_amount_currency = diff_balance = difference
            else:
                diff_amount_currency = difference
                diff_balance = self.currency_id._convert(diff_amount_currency, self.company_id.currency_id, self.company_id, self.invoice_date or self.date)
            return diff_balance, diff_amount_currency

        def _apply_cash_rounding(self, diff_balance, diff_amount_currency, cash_rounding_line):
            rounding_line_vals = {
                'balance': diff_balance,
                'amount_currency': diff_amount_currency,
                'partner_id': self.partner_id.id,
                'move_id': self.id,
                'currency_id': self.currency_id.id,
                'company_id': self.company_id.id,
                'company_currency_id': self.company_id.currency_id.id,
                'display_type': 'rounding',
            }

            rounding_method = self.invoice_cash_rounding_id

            if rounding_method.strategy == 'biggest_tax':
                biggest_tax_line = None
                for tax_line in self.line_ids.filtered('tax_repartition_line_id'):
                    if not biggest_tax_line or abs(tax_line.balance) > abs(biggest_tax_line.balance):
                        biggest_tax_line = tax_line

                if not biggest_tax_line:
                    return

                rounding_line_vals.update({
                    'name': _('%s (rounding)', biggest_tax_line.name),
                    'account_id': biggest_tax_line.account_id.id,
                    'tax_repartition_line_id': biggest_tax_line.tax_repartition_line_id.id,
                    'tax_tag_ids': [(6, 0, biggest_tax_line.tax_tag_ids.ids)],
                    'tax_ids': [Command.set(biggest_tax_line.tax_ids.ids)]
                })

            elif rounding_method.strategy == 'add_invoice_line':
                if diff_balance > 0.0 and rounding_method.loss_account_id:
                    account_id = rounding_method.loss_account_id.id
                else:
                    account_id = rounding_method.profit_account_id.id

                rounding_line_vals['account_id'] = account_id
                rounding_line_vals['tax_ids'] = [Command.clear()]

                if rounding_method.product_id:
                    product = rounding_method.product_id
                    rounding_line_vals.update({
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'name': product.partner_ref or product.name,
                    })
                else:
                    rounding_line_vals['name'] = rounding_method.name

            if cash_rounding_line:
                cash_rounding_line.write(rounding_line_vals)
            else:
                cash_rounding_line = self.env['account.move.line'].create(rounding_line_vals)

        existing_cash_rounding_line = self.line_ids.filtered(lambda line: line.display_type == 'rounding')

        if not self.invoice_cash_rounding_id:
            existing_cash_rounding_line.unlink()
            return

        if self.invoice_cash_rounding_id and existing_cash_rounding_line:
            strategy = self.invoice_cash_rounding_id.strategy
            old_strategy = 'biggest_tax' if existing_cash_rounding_line.tax_line_id else 'add_invoice_line'
            if strategy != old_strategy:
                existing_cash_rounding_line.unlink()
                existing_cash_rounding_line = self.env['account.move.line']

        others_lines = self.line_ids.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
        others_lines -= existing_cash_rounding_line
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        diff_balance, diff_amount_currency = _compute_cash_rounding(self, total_amount_currency)

        if self.currency_id.is_zero(diff_balance) and self.currency_id.is_zero(diff_amount_currency):
            existing_cash_rounding_line.unlink()
            return

        if existing_cash_rounding_line \
            and float_compare(existing_cash_rounding_line.balance, diff_balance, precision_rounding=self.currency_id.rounding) == 0 \
            and float_compare(existing_cash_rounding_line.amount_currency, diff_amount_currency, precision_rounding=self.currency_id.rounding) == 0:
            return

        _apply_cash_rounding(self, diff_balance, diff_amount_currency, existing_cash_rounding_line)
