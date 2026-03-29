{
    'name': 'FastAPI Base V19',
    'summary': 'Standalone FastAPI Framework for Odoo 19',
    'version': '1.0',
    'category': 'Tools',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/fastapi_endpoint_views.xml',
    ],
    'installable': True,
    'author': 'nada,amr',
    'license': 'LGPL-3',
}
