from odoo import models, fields, api

class UoM(models.Model):
    _name = 'uom.uom'
    _description = 'Unit of Measure'

    name = fields.Char(string='Unit Name', required=True)
    factor = fields.Float(string='Conversion Factor', required=True, help='Factor used to convert this unit to the reference unit of its category')
    active = fields.Boolean(string='Active', default=True)
    rounding = fields.Float(string='Rounding Precision', default=0.01, help='Rounding applied to quantities in this unit of measure')
