from odoo import models, fields, api, exceptions

class Product(models.Model):
    _name = 'stock.product'
    _description = 'Stock Product'


    name = fields.Char(string='Product Name', required=True)
    sku = fields.Char(string='SKU', required=True)
    barcode = fields.Char(string='Barcode', required=True)
    warehouse_id = fields.Many2one('stock.loc', string='Initial Warehouse', required=True)
    category_id = fields.Many2one('stock.category', string='Category', required=True)
    quantity_on_hand = fields.Float(string='Quantity on Hand', store=True)
    quantity = fields.Float(string='Quantity', compute='_compute_quantity', store=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    weight = fields.Float(string='Weight')
    dimensions = fields.Char(string='Dimensions (L x W x H)')

    # One-to-many relation to stock.quan for tracking quantities in multiple locations
    stock_quant_ids = fields.One2many('stock.quan', 'product_id', string='Stock Quantities')

    @api.depends('stock_quant_ids')
    def _compute_quantity(self):
        """
        Compute the total quantity on hand for the product across all locations.
        """
        for record in self:
            record.quantity = sum(record.stock_quant_ids.mapped('quantity'))



    def write(self, vals):
        """
        Override write to handle updates to the warehouse and ensure consistency in stock.quan.
        """
        res = super(Product, self).write(vals)
        for record in self:
            if 'warehouse_id' in vals and record.warehouse_id:
                # Check if a stock.quan exists for the new warehouse
                stock_quant = self.env['stock.quan'].search([
                    ('product_id', '=', record.id),
                    ('location_id', '=', record.warehouse_id.id)
                ], limit=1)
                if not stock_quant:
                    self.env['stock.quan'].create({
                        'product_id': record.id,
                        'location_id': record.warehouse_id.id,
                        'quantity': 0.0,  # Initialize stock for the new warehouse
                    })
        return res

    """
    créez automatiquement un enregistrement dans stock.quan pour chaque produit créé,
    """
    @api.model
    def create(self, vals):
        product = super(Product, self).create(vals)
        if product.warehouse_id:
            self.env['stock.quan'].create({
                'product_id': product.id,
                'location_id': product.warehouse_id.id,
                'quantity': product.quantity_on_hand or 0.0
            })
        return product
    