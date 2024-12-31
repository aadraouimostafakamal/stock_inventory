from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockReorderingRule(models.Model):
    _name = 'stock.reordering.rule'
    _description = 'Stock Reordering Rule'

    product_id = fields.Many2one('stock.product', string="Product", required=True)
    warehouse_id = fields.Many2one('stock.loc', string="Warehouse", required=True)
    min_quantity = fields.Float(string="Minimum Quantity", required=True)
    max_quantity = fields.Float(string="Maximum Quantity", required=True)
    qty_multiple = fields.Float(string="Quantity Multiple", default=1.0)
    notification_sent = fields.Boolean(string="Notification Sent", default=False)
    current_stock = fields.Float(string="Current Stock", compute='_compute_current_stock', store=False)

    @api.depends('product_id.quantity_on_hand')
    def _compute_current_stock(self):
        """
        Use the `quantity_on_hand` field directly from the `stock.product` model.
        """
        for rule in self:
            rule.current_stock = rule.product_id.quantity_on_hand or 0.0
            rule._check_stock_alert()

    def _check_stock_alert(self):
        """
        Check if the stock is below the minimum quantity and send notifications if needed.
        """
        for rule in self:
            if rule.current_stock < rule.min_quantity:
                if not rule.notification_sent:
                    # Create notification if not already sent
                    rule._create_notification()
                    rule.notification_sent = True
            else:
                # Reset notification flag if stock is replenished
                rule.notification_sent = False

    def _create_notification(self):
        """
        Create a low stock notification using Odoo's messaging system.
        """
        for rule in self:
            message_body = (
                f"<b>⚠️ Low Stock Alert:</b><br/>"
                f"Product: <b>{rule.product_id.name}</b><br/>"
                f"Current Stock: <b>{rule.current_stock}</b><br/>"
                f"Minimum Required: <b>{rule.min_quantity}</b>"
            )
            self.env['mail.message'].create({
                'message_type': "notification",
                'body': message_body,
                'subject': "Low Stock Alert",
                'model': self._name,
                'res_id': rule.id,
                'subtype_id': self.env.ref('mail.mt_note').id,
                'partner_ids': [(4, self.env.user.partner_id.id)]
            })
