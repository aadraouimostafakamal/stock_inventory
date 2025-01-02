from odoo import models, fields, api, exceptions

class StockMovement(models.Model):
    _name = 'stock.movement'
    _description = 'Stock Movement'

    product_id = fields.Many2one('stock.product', string="Product", required=True)
    source_location_id = fields.Many2one('stock.loc', string="Source Location", required=True)
    destination_location_id = fields.Many2one('stock.loc', string="Destination Location", required=True)
    quantity = fields.Float(string="Quantity", required=True)
    max_quantity = fields.Float(string="Maximum Quantity", compute='_compute_max_quantity', store=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='État', default='draft', required=True)

    @api.depends('product_id', 'source_location_id')
    def _compute_max_quantity(self):
        for record in self:
            record.max_quantity = 0.0
            
            if not record.product_id or not record.source_location_id:
                continue

            stock_quants = self.env['stock.quan'].search([
                ('product_id', '=', record.product_id.id),
                ('location_id', '=', record.source_location_id.id)
            ])

            if stock_quants:
                record.max_quantity = sum(stock_quants.mapped('quantity'))

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            record._compute_max_quantity()
            
            if record.quantity <= 0:
                raise exceptions.ValidationError(
                    'La quantité doit être supérieure à 0.'
                )
                
            if record.quantity > record.max_quantity:
                raise exceptions.ValidationError(
                    f'La quantité ({record.quantity}) ne peut pas dépasser '
                    f'la quantité disponible ({record.max_quantity}) pour le produit '
                    f'{record.product_id.name} dans l\'emplacement {record.source_location_id.name}.'
                )

    def _validate_movement(self):
        self.ensure_one()
        
        # Recheck quantity before validation
        self._check_quantity()
        
        source_stock_line = self.env['stock.quan'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.source_location_id.id)
        ], limit=1)

        if not source_stock_line or source_stock_line.quantity < self.quantity:
            raise exceptions.UserError(
                f"Quantité insuffisante dans l'emplacement source. "
                f"Disponible: {source_stock_line.quantity if source_stock_line else 0}, "
                f"Demandé: {self.quantity}"
            )

        # Use sudo() to ensure we have the necessary permissions
        source_stock_line.sudo().write({'quantity': source_stock_line.quantity - self.quantity})

        dest_stock_line = self.env['stock.quan'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.destination_location_id.id)
        ], limit=1)

        if dest_stock_line:
            dest_stock_line.sudo().write({'quantity': dest_stock_line.quantity + self.quantity})
        else:
            self.env['stock.quan'].sudo().create({
                'product_id': self.product_id.id,
                'location_id': self.destination_location_id.id,
                'quantity': self.quantity,
            })

    def action_validate(self):
        """
        Custom method to validate the movement
        """
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError('Only draft movements can be validated.')
            record._validate_movement()
            record.write({'state': 'done'})

    def write(self, vals):
        """
        Override write method to handle state changes
        """
        if vals.get('state') == 'done' and any(rec.state != 'draft' for rec in self):
            raise exceptions.UserError(
                'Invalid state transition. Use the validate button to process movements.'
            )
        return super(StockMovement, self).write(vals)