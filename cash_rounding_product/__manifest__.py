{
    'name': 'Cash Rounding Product',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Assign a product to cash rounding methods for invoice lines',
    'description': """
Cash Rounding Product
=====================

This module extends the Cash Rounding model to allow assigning a product
to each rounding method. When a rounding line is created on an invoice
(manually or from POS), it uses the configured product instead of just
the rounding name.

Features:
- Add a product field to Cash Rounding methods
- Rounding invoice lines use the product's code, name, and taxes
- Works with both 'Add a rounding line' and POS rounding strategies
""",
    'author': 'Codeapps - Javier Pepe',
    'depends': ['account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_cash_rounding_views.xml',
        'data/rounding_product_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
