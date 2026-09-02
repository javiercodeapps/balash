# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    product_id = fields.Many2one(
        'product.product', 
        string='Producto de Redondeo (AFIP)',
        domain=[('type', '=', 'service')],
        help="Producto con IVA Exento o 0% indispensable para la validación de ARCA"
    )

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _create_invoice(self, move_vals):
        """
        Heredamos la creación de facturas desde el POS para forzar 
        la inyección de la línea de producto de redondeo.
        """
        # 1. Dejamos que Odoo cree el borrador de la factura normalmente
        new_move = super(PosOrder, self)._create_invoice(move_vals)

        cash_rounding = getattr(self.config_id, 'rounding_method', False) or getattr(self.config_id, 'cash_rounding_id', False)
        
        for move in new_move:
            for line in move.invoice_line_ids:
            # 2. Si la factura tiene redondeo contable y tu producto configurado
            if cash_rounding and cash_rounding.product_id:
                rounding_product = cash_rounding.product_id
                
                # Buscamos las líneas de redondeo técnicas ocultas que rompen ARCA
                rounding_lines = move.line_ids.filtered(lambda l: l.display_type == 'rounding')
                if rounding_lines:
                    rounding_amount = sum(line.balance for line in rounding_lines)
                    
                    # Eliminamos la línea técnica nativa
                    move.line_ids -= rounding_lines
                    
                    # Calculamos el precio unitario correcto para el producto
                    price_unit = -rounding_amount if move.is_sale_document() else rounding_amount
                    
                    # 3. Creamos e inyectamos la línea comercial real que AFIP exige
                    new_rounding_line = self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'move_id': move.id,
                        'product_id': rounding_product.id,
                        'name': rounding_product.display_name,
                        'quantity': 1.0,
                        'price_unit': price_unit,
                        'product_uom_id': rounding_product.uom_id.id,
                        'display_type': 'product',
                        'tax_ids': [(6, 0, rounding_product.taxes_id.filtered(lambda t: t.company_id == move.company_id).ids)] if rounding_product.taxes_id else [],
                    })
                    
                    
                    # 4. Forzamos el recálculo total de la factura para reestructurar la polinómica de AFIP
                    move._compute_tax_totals()
                    
        return new_move
