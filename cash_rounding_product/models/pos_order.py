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

        for move in new_move:
            # --- LOG DE DIAGNÓSTICO: Inspección Inicial ---
            _logger.info("=================== INTERCEPTANDO FACTURA DESDE POS ===================")
            _logger.info("Factura ID: %s | Origen POS: %s", move.id, move.invoice_origin)
            _logger.info("¿Tiene método de redondeo?: %s", move.cash_rounding_id.name if move.cash_rounding_id else 'NO')
            
            _logger.info("PRODUCTOS INICIALES ENVIADOS POR EL POS:")
            for line in move.invoice_line_ids:
                _logger.info(
                    "- %s | Cant: %s | Precio: %s | Impuestos ID: %s",
                    line.product_id.name, line.quantity, line.price_unit, line.tax_ids.ids
                )
            _logger.info("====================================================================")

            # 2. Si la factura tiene redondeo contable y tu producto configurado
            if move.cash_rounding_id and move.cash_rounding_id.product_id:
                rounding_product = move.cash_rounding_id.product_id
                
                # Buscamos las líneas de redondeo técnicas ocultas que rompen ARCA
                rounding_lines = move.line_ids.filtered(lambda l: l.is_rounding_line)
                
                if rounding_lines:
                    rounding_amount = sum(line.balance for line in rounding_lines)
                    _logger.info(">>> Redondeo técnico nativo detectado en asiento: %s. Reemplazando...", rounding_amount)
                    
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
                    
                    _logger.info(">>> ¡Línea de producto de redondeo creada exitosamente en la factura!")
                    
                    # 4. Forzamos el recálculo total de la factura para reestructurar la polinómica de AFIP
                    move._compute_tax_totals()
                    
                    _logger.info(">>> NUEVO TOTAL DE LA FACTURA RECALCULADO: %s", move.amount_total)
                    _logger.info("====================================================================")
                    
        return new_move
