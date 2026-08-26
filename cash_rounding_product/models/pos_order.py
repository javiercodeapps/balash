from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_aml_values_list_per_nature(self):
        aml_vals_list_per_nature = super()._prepare_aml_values_list_per_nature()

        cash_rounding = self.config_id.rounding_method
        if cash_rounding and cash_rounding.product_id:
            for aml_vals in aml_vals_list_per_nature.get('cash_rounding', []):
                if aml_vals.get('display_type') == 'rounding' and not aml_vals.get('product_id'):
                    aml_vals['product_id'] = cash_rounding.product_id.id
                    aml_vals['product_uom_id'] = cash_rounding.product_id.uom_id.id

        return aml_vals_list_per_nature
