{
    'name': 'Third Party API',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Customer, Debtor, Contact, Invoice & Payment Management via FastAPI',
    'description': '''
        RESTful API for managing partners, invoices, and payments from third-party systems.
        
        Endpoints:
        - POST /customer - Create or update customers by reference
        - POST /debtor - Create invoice contacts linked to customers
        - POST /contact - Create contacts with optional company linkage
        - POST /invoice - Create customer invoices with facility type & payout
        - POST /payment - Create payments with cheque details
        
        All endpoints require JWT Bearer token authentication.
        
        New Fields Added:
        - account.move: facility_type_id, payout_id, contract_no
        - account.payment: check_name, cheque_no, due_date, check_status, payout_id, cheque_type
        - product.template: analytic_plan_id
        - account.analytic.plan: code
    ''',
    'depends': ['base', 'account', 'analytic', 'product', 'mail', 'base_automation', 'fastapi_v19_authentication'],
    'data': [
        'security/ir.model.access.csv',
        'data/fastapi_endpoint.xml',
        'data/sarwa_config.xml',
        'data/sarwa_automation.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/product_template_views.xml',
        'views/account_analytic_plan_views.xml',
        'views/account_journal_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'external_dependencies': {
        'python': ['pydantic', 'requests'],
    },
    'author': 'Enmaa',
    'installable': True,
    'license': 'LGPL-3',
}
