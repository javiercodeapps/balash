{
    'name': 'POS Journal Auto',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Auto-assign billing journals to POS payment methods and switch invoices from preprinted to electronic journals.',
    'description': """
POS Journal Auto
================

* Each Point of Sale payment method can be assigned a billing (invoice) journal. When an
  invoice is generated from the POS, the billing journal is chosen automatically from the
  payment method(s) used in the order, falling back to the POS config journal.

* Invoices generated in a preprinted journal (Argentina l10n_ar_afip_pos_system 'II_IM')
  can be voided and re-issued in an electronic journal through a wizard launched from the
  invoice form ("Change to Electronic Journal").
""",
    'author': 'Exlim',
    'depends': ['point_of_sale', 'l10n_ar'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
        'views/pos_journal_auto_switch_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_journal_auto/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
