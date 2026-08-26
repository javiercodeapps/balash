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


# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

# Inicializamos el logger de Odoo
_logger = logging.getLogger(__name__)

class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    product_id = fields.Many2one(
        'product.product', 
        string='Producto de Redondeo (AFIP)',
        domain=[('type', '=', 'service')],
        help="Producto con IVA Exento o 0% indispensable para la validación de ARCA"
    )

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('invoice_line_ids')
    def _compute_cash_rounding(self):
        """
        Intercepta el cálculo nativo de redondeo, inyecta la diferencia
        como un producto comercial real e imprime los logs de control.
        """
        super(AccountMove, self)._compute_cash_rounding()

        for move in self:
            # --- LOG DE DIAGNÓSTICO: Productos antes del proceso ---
            _logger.info("=================== AUDITORÍA DE FACTURA POS: %s ===================", move.name or 'Borrador')
            _logger.info("PRODUCTOS DETECTADOS EN LA FACTURA ANTES DEL REDONDEO:")
            for line in move.invoice_line_ids:
                _logger.info(
                    "- Producto: %s | Cantidad: %s | Precio Unitario: %s | Total Línea: %s | Impuestos ID: %s",
                    line.product_id.name, 
                    line.quantity, 
                    line.price_unit, 
                    line.price_total,
                    line.tax_ids.ids
                )
            _logger.info("Monto Total de la Factura (ImpTotal): %s", move.amount_total)
            _logger.info("====================================================================")

            if move.cash_rounding_id and move.cash_rounding_id.rounding_product_id and move.is_invoice():
                rounding_product = move.cash_rounding_id.product_id
                rounding_lines = move.line_ids.filtered(lambda l: l.is_rounding_line)
                
                if rounding_lines:
                    rounding_amount = sum(line.balance for line in rounding_lines)
                    
                    _logger.info(">>> Redondeo técnico nativo detectado: %s. Reemplazando por línea de producto...", rounding_amount)
                    
                    # Eliminamos la línea técnica nativa que rompe la polinómica
                    move.line_ids -= rounding_lines
                    
                    # Calculamos el precio según el tipo de documento
                    price_unit = -rounding_amount if move.is_sale_document() else rounding_amount
                    
                    # Inyectamos la línea comercial real
                    new_rounding_line = self.env['account.move.line'].new({
                        'move_id': move.id,
                        'product_id': rounding_product.id,
                        'name': rounding_product.display_name,
                        'quantity': 1.0,
                        'price_unit': price_unit,
                        'product_uom_id': rounding_product.uom_id.id,
                        'display_type': 'product',
                    })
                    
                    if rounding_product.taxes_id:
                        company_taxes = rounding_product.taxes_id.filtered(lambda t: t.company_id == move.company_id)
                        new_rounding_line.tax_ids = [(6, 0, company_taxes.ids)]
                    
                    move.invoice_line_ids += new_rounding_line
                    
                    # Forzamos el recálculo general
                    move._compute_tax_totals()
                    
                    # --- LOG DE DIAGNÓSTICO: Verificación Post-Inyección ---
                    _logger.info(">>> LÍNEA DE REDONDEO INYECTADA CON ÉXITO:")
                    _logger.info("- Producto: %s | Precio: %s | Impuestos: %s", rounding_product.name, price_unit, new_rounding_line.tax_ids.ids)
                    _logger.info("Nuevo Monto Total Calculado (Post-Redondeo): %s", move.amount_total)
                    _logger.info("====================================================================")