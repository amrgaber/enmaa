{
    'name': 'FastAPI V19 Authentication',
    'summary': 'Centralized JWT Authentication for FastAPI Third-Party APIs',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'author': 'nada,amr',
    'depends': ['fastapi_base_v19'],
    'data': [
        'security/ir.model.access.csv',
        'data/auth_params.xml',
    ],
    'external_dependencies': {
        'python': ['pydantic', 'pyjwt'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
