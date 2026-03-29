{
    'name': 'Payment Third Party API',
    'summary': 'Expose FastAPI endpoints for creating payments from third-party systems',
    'version': '1.0.0',
    'category': 'Accounting',
    'author': 'nada,amr',
    'depends': ['account', 'fastapi_v19_authentication', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'data/fastapi_endpoint.xml',
        'views/account_journal_views.xml',
        'views/account_payment_method_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
