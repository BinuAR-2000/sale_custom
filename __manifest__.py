# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale custom',
    'category': 'Sales',
    'sequence': 10,
    'website': '',
    'summary': 'Managing sales',
    'version': '17.0',
    'author' : 'Binu A R',
    'description': """
        Managing sales
        """,
    'depends': ['base','sale','sale_management','stock','account'],

    'data': [
        'data/res_group_data.xml',
        'view/sale_order_view.xml',
        'view/res_config_settings_views.xml',
    #     'views/website_banner_views.xml',
    ],
    'installable': True,
    # 'application': True,
    'license': 'LGPL-3',
}
