{
    'name': 'Account Third Party API',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Create invoices via FastAPI from third-party systems',
    'depends': ['account', 'fastapi_v19_authentication', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'data/fastapi_endpoint.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/account_account_views.xml',
        'views/account_analytic_views.xml',
    ],
    'external_dependencies': {
        'python': ['pydantic'],
    },
    'author': 'nada,amr',
    'installable': True,
    'license': 'LGPL-3',
}

