from odoo import models, fields, api


class ResConfigSetting(models.TransientModel):
    _inherit='res.config.settings'
    _description = 'Res Config Setting'

    is_sale_limit = fields.Boolean('Is Sale Limit')
    sale_limit = fields.Float('Sale Limit')
    is_auto_workflow= fields.Boolean('Auto Work Flow')

    def set_values(self):
        res = super(ResConfigSetting, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sale_custom.is_sale_limit',
                                                         self.is_sale_limit)
        self.env['ir.config_parameter'].sudo().set_param('sale_custom.sale_limit',
                                                         self.sale_limit)
        self.env['ir.config_parameter'].sudo().set_param('sale_custom.is_auto_workflow',
                                                         self.is_auto_workflow)


        return res

    def get_values(self):
        sup = super(ResConfigSetting, self).get_values()
        with_user = self.env['ir.config_parameter'].sudo()
        sale_limit = with_user.get_param('sale_custom.sale_limit')
        is_sale_limit = with_user.get_param('sale_custom.is_sale_limit')
        is_auto_workflow = with_user.get_param('sale_custom.is_auto_workflow')


        sup.update(sale_limit= sale_limit,
                   is_sale_limit=is_sale_limit,is_auto_workflow=is_auto_workflow)
        return sup
