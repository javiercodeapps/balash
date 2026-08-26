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

        existing_rounding = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
        _logger.warning(
            "  EXISTING rounding lines: %s (count=%d)",
            existing_rounding.ids, len(existing_rounding),
        )
        for rl in existing_rounding:
            _logger.warning(
                "    line id=%s name=%s product=%s amount_currency=%s balance=%s account=%s",
                rl.id, rl.name, rl.product_id.display_name,
                rl.amount_currency, rl.balance, rl.account_id.display_name,
            )

        super()._recompute_cash_rounding_lines()

        after_rounding = self.line_ids.filtered(lambda line: line.display_type == 'rounding')
        _logger.warning(
            "  AFTER SUPER rounding lines: %s (count=%d)",
            after_rounding.ids, len(after_rounding),
        )
        for rl in after_rounding:
            _logger.warning(
                "    line id=%s name=%s product=%s amount_currency=%s balance=%s account=%s",
                rl.id, rl.name, rl.product_id.display_name,
                rl.amount_currency, rl.balance, rl.account_id.display_name,
            )

        rounding_method = self.invoice_cash_rounding_id
        if rounding_method and rounding_method.product_id:
            for rl in after_rounding:
                if not rl.product_id:
                    rl.write({'product_id': rounding_method.product_id.id})
                    _logger.warning("  SET product_id=%s on line %s", rounding_method.product_id.id, rl.id)

        _logger.warning("=== CASH ROUNDING RECOMPUTE END ===")
