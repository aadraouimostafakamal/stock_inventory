from odoo import models, fields, api

class Category(models.Model):
    _name = 'stock.category'
    _description = 'Stock Category'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('stock.category', string='Parent Category', help='Parent category for hierarchical structure')
    child_ids = fields.One2many('stock.category', 'parent_id', string='Subcategories')
    is_active = fields.Boolean(string='Active', default=True)
