{
    'name': 'Webhook Receiver',
    'version': '19.0.1.0.0',
    'summary': 'Receive webhook requests and store as JSON logs',
    'category': 'Technical',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/webhook_log_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
