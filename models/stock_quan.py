from odoo import models, fields

class StockQuant(models.Model):
    _name = 'stock.quan'
    _description = 'Stock Quant'

    product_id = fields.Many2one('stock.product', string="Product", required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.loc', string="Location", required=True)
    quantity = fields.Float(string="Quantity", required=True, default=0.0)
