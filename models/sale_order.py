from itertools import groupby

from odoo import models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_is_zero


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale order'

    # Custom    Field    Addition
    manager_ref = fields.Char("Manager Reference", copy=False)
    is_sale_admin = fields.Boolean(
        string="Is Sale Admin",
        compute='_compute_is_sale_admin',
        store=False, copy=False
    )

    def _compute_is_sale_admin(self):

        '''Check the User has Sales admin access'''
        for record in self:
            record.is_sale_admin = False
            record.is_sale_admin = self.env.user.has_group('sale_custom.sale_admin_groups')

    def action_confirm(self):
        for rec in self:
            res = super(SaleOrder, self).action_confirm()
            ICP = self.env['ir.config_parameter'].sudo()
            sale_limit = float(ICP.get_param('sale_custom.sale_limit'))
            is_sale_limit = ICP.get_param('sale_custom.is_sale_limit')
            is_auto_workflow = ICP.get_param('sale_custom.is_auto_workflow')
            if not is_auto_workflow and not is_sale_limit:
                return res
            elif not is_auto_workflow and is_sale_limit:
                if rec.amount_total >= sale_limit:
                    if not rec.is_sale_admin:
                        raise ValidationError(
                            _('The order cannot be confirmed because the total amount exceeds the allowed sale limit of configured sale limit.'))

                    return res
                else:
                    return res
            elif is_auto_workflow and not is_sale_limit:
                picking_ids = rec.picking_ids
                for picking in picking_ids:
                    for move in picking.move_ids_without_package:
                        move.quantity = move.product_uom_qty
                    picking.button_validate()

                    if not rec.invoice_ids:
                        invoice_created = rec._create_invoices(rec) if rec else False
                        if invoice_created:
                            invoice_created.action_post()
                        self.env['account.payment.register'].with_context(active_model='account.move',
                                                                          active_ids=invoice_created.ids).create({
                            'payment_date': invoice_created.date,
                        })._create_payments()
                    return res
            elif is_auto_workflow and is_sale_limit:
                if rec.amount_total >= sale_limit:
                    if not rec.is_sale_admin:
                        raise ValidationError(
                            _('The order cannot be confirmed because the total amount exceeds the allowed sale limit of configured sale limit.'))
                    picking_ids = rec.picking_ids
                    for picking in picking_ids:
                        for move in picking.move_ids_without_package:
                            move.quantity = move.product_uom_qty
                        picking.button_validate()

                        if not rec.invoice_ids:
                            invoice_created = rec._create_invoices(rec) if rec else False
                            if invoice_created:
                                invoice_created.action_post()
                            self.env['account.payment.register'].with_context(active_model='account.move',
                                                                              active_ids=invoice_created.ids).create({
                                'payment_date': invoice_created.date,
                            })._create_payments()
                    return res
                else:
                    picking_ids = rec.picking_ids
                    for picking in picking_ids:
                        for move in picking.move_ids_without_package:
                            move.quantity = move.product_uom_qty
                        picking.button_validate()

                        if not rec.invoice_ids:
                            invoice_created = rec._create_invoices(rec) if rec else False
                            if invoice_created:
                                invoice_created.action_post()
                            self.env['account.payment.register'].with_context(active_model='account.move',
                                                                              active_ids=invoice_created.ids).create({
                                'payment_date': invoice_created.date,
                            })._create_payments()
                    return res


class StockMove(models.Model):
    """inheriting the stock move model"""
    _inherit = 'stock.move'

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        ICP = self.env['ir.config_parameter'].sudo()
        sale_limit = float(ICP.get_param('sale_custom.sale_limit'))
        is_sale_limit = ICP.get_param('sale_custom.is_sale_limit')
        is_auto_workflow = ICP.get_param('sale_custom.is_auto_workflow')
        if not is_auto_workflow:
            return super(StockMove,self)._assign_picking()
        else:
            Picking = self.env['stock.picking']
            grouped_moves = groupby(self, key=lambda m: m._key_assign_picking())
            for group, moves in grouped_moves:
                moves = self.env['stock.move'].concat(*moves)
                new_picking = False
                # Could pass the arguments contained in group but they are the same
                # for each move that why moves[0] is acceptable
                picking = moves[0]._search_picking_for_assignation()
                if picking:
                    # If a picking is found, we'll append `move` to its move list and thus its
                    # `partner_id` and `ref` field will refer to multiple records. In this
                    # case, we chose to wipe them.
                    vals = {}
                    if any(picking.partner_id.id != m.partner_id.id for m in moves):
                        vals['partner_id'] = False
                    if any(picking.origin != m.origin for m in moves):
                        vals['origin'] = False
                    if vals:
                        picking.write(vals)
                    moves.write({'picking_id': picking.id})
                    moves._assign_picking_post_process(new=new_picking)
                else:
                    # Don't create picking for negative moves since they will be
                    # reverse and assign to another picking
                    moves = moves.filtered(lambda m: float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) >= 0)
                    if not moves:
                        continue
                    new_picking = True
                    move_line = sorted(moves,
                                        key=lambda x: x.product_id.id)
                    for product_id, lines in groupby(move_line,
                                                      key=lambda
                                                              x: x.product_id):
                       # Convert _grouper to list
                       lines = list(lines)

                       # Sum the quantity for the same product lines
                       total_qty = sum(line.product_uom_qty for line in lines)
                       # line = lines[0]
                       for line in lines:
                        line['quantity']=line.product_uom_qty
                       # line['quantity']=total_qty

                       new_moves = self.env['stock.move'].concat(*lines)
                       picking = picking.create(
                           new_moves._get_new_picking_values())
                       new_moves.write({'picking_id': picking.id})
                       new_moves._assign_picking_post_process(new=new_picking)
                       # new_moves.quantity = total_qty

                       # new_moves.picking_id._should_show_transfers()

                       new_moves.picking_id.button_validate()



            return True



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _sanity_check(self, separate_pickings=True):
        """ Sanity check for `button_validate()`
            :param separate_pickings: Indicates if pickings should be checked independently for lot/serial numbers or not.
        """
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        pickings_without_moves = self.filtered(lambda p: not p.move_ids and not p.move_line_ids)
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        no_quantities_done_ids = set()
        ICP = self.env['ir.config_parameter'].sudo()

        is_auto_workflow = ICP.get_param('sale_custom.is_auto_workflow')

        pickings_without_quantities = self.env['stock.picking']
        for picking in self:

            if not is_auto_workflow and all(float_is_zero(move.quantity, precision_digits=precision_digits) for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))):
                pickings_without_quantities |= picking

        pickings_using_lots = self.filtered(lambda p: p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots)
        if pickings_using_lots:
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(no_quantities_done_ids, separate_pickings)
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    pickings_without_lots |= line.picking_id
                    products_without_lots |= line.product_id

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_("You can’t validate an empty transfer. Please add some products to move before proceeding."))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.', ', '.join(products_without_lots.mapped('display_name'))))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.', ', '.join(pickings_without_moves.mapped('name')))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.', ', '.join(pickings_without_lots.mapped('name')), ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())


