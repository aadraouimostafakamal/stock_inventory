from odoo import models, fields, api

class StockLocation(models.Model):
    _name = 'stock.loc'
    _description = 'Stock Location'

    name = fields.Char(string="Location Name", required=True)
    parent_id = fields.Many2one('stock.loc', string="Parent Location")
    address = fields.Text(string="Address")
    usage = fields.Selection(
        [('internal', 'Internal'), ('customer', 'Customer'), ('supplier', 'Supplier'), ('inventory_loss', 'Inventory Loss')],
        string="Usage", required=True, default='internal'
    )
    is_active = fields.Boolean(string="Is Active", default=True)
