import logging

from odoo import fields, models

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
        _logger.warning(
            "=== CASH ROUNDING RECOMPUTE START move=%s invoice_cash_rounding_id=%s ===",
            self.id, self.invoice_cash_rounding_id.id,
        )
        _logger.warning(
            "  rounding method: name=%s strategy=%s rounding=%s rounding_method=%s",
            self.invoice_cash_rounding_id.name,
            self.invoice_cash_rounding_id.strategy,
            self.invoice_cash_rounding_id.rounding,
            self.invoice_cash_rounding_id.rounding_method,
        )
        _logger.warning(
            "  profit_account=%s loss_account=%s product=%s",
            self.invoice_cash_rounding_id.profit_account_id.display_name,
            self.invoice_cash_rounding_id.loss_account_id.display_name,
            self.invoice_cash_rounding_id.product_id.display_name,
        )

        existing_rounding = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
        _logger.warning(
            "  BEFORE: rounding lines=%s count=%d",
            existing_rounding.ids, len(existing_rounding),
        )

        super()._recompute_cash_rounding_lines()

        all_lines = self.line_ids.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
        _logger.warning("  ALL non-bank lines after super:")
        for l in all_lines:
            _logger.warning(
                "    id=%s display_type=%s name=%s product=%s amount_currency=%s balance=%s account=%s taxes=%s",
                l.id, l.display_type, l.name,
                l.product_id.display_name or False,
                l.amount_currency, l.balance,
                l.account_id.display_name,
                l.tax_ids.ids,
            )

        rounding_method = self.invoice_cash_rounding_id
        if rounding_method and rounding_method.product_id:
            rounding_lines = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
            for rl in rounding_lines:
                if not rl.product_id:
                    rl.write({'product_id': rounding_method.product_id.id})
                    _logger.warning("  SET product_id=%s on line %s", rounding_method.product_id.id, rl.id)

        _logger.warning("=== CASH ROUNDING RECOMPUTE END ===")
