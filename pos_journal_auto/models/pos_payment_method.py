from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    invoice_journal_id = fields.Many2one(
        'account.journal',
        string='Billing Journal',
        domain="[('type', '=', 'sale')]",
        check_company=True,
        help="Journal used to generate the customer invoice when this payment method is used. "
             "Leave empty to use the journal configured on the POS config.",
    )
