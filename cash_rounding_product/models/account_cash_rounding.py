import logging

from odoo import Command, fields, models, api
from odoo.tools import float_compare, float_round

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

    @api.depends('invoice_line_ids')
    def _compute_cash_rounding(self):
        """
        Odoo nativo calcula el redondeo y crea una línea huérfana en 'line_ids'.
        Heredamos el método para forzar que esa línea use tu producto y sus impuestos.
        """
        # Ejecutamos primero el cálculo nativo de Odoo para que cree la diferencia
        super(AccountMove, self)._compute_cash_rounding()

        for move in self:
            # Si la factura tiene un método de redondeo asignado y tiene tu producto configurado
            if move.cash_rounding_id and move.cash_rounding_id.rounding_product_id:
                rounding_product = move.cash_rounding_id.product_id
                
                # Buscamos la línea de redondeo que Odoo acaba de crear en el asiento (suele no tener product_id)
                rounding_lines = move.line_ids.filtered(lambda l: l.is_rounding_line)
                
                for line in rounding_lines:
                    # Forzamos los datos del producto para que la Localización Argentina la procese correctamente
                    line.write({
                        'product_id': rounding_product.id,
                        'name': rounding_product.display_name or line.name,
                        'product_uom_id': rounding_product.uom_id.id,
                        # Sincronizamos las cuentas contables del producto si es necesario
                        'account_id': rounding_product.property_account_income_id.id or line.account_id.id,
                    })
                    
                    # ASIGNACIÓN DE IMPUESTOS: Clave para AFIP
                    if rounding_product.taxes_id:
                        # Filtrar impuestos correctos según la compañía de la factura
                        taxes = rounding_product.taxes_id.filtered(lambda t: t.company_id == move.company_id)
                        line.tax_ids = [(6, 0, taxes.ids)]
