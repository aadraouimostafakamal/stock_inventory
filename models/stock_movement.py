from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)

class StockMovement(models.Model):
    _name = 'stock.movement'
    _description = 'Stock Movement'

    product_id = fields.Many2one('stock.product', string="Product", required=True)
    source_location_id = fields.Many2one('stock.loc', string="Source Location", required=True)
    destination_location_id = fields.Many2one('stock.loc', string="Destination Location", required=True)
    quantity = fields.Float(string="Quantity", required=True)
    max_quantity = fields.Float(string="Maximum Quantity", compute='_compute_max_quantity', store=False)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé'),
        ('cancelled', 'Annulé')
    ], string='État', default='done', required=True)

    @api.depends('product_id', 'source_location_id')
    def _compute_max_quantity(self):
        """
        Compute the maximum quantity available in the source location for the product.
        """
        for record in self:
            record.max_quantity = 0.0  # Default value
            
            if not record.product_id or not record.source_location_id:
                _logger.debug(f"Missing product or location for record {record.id}")
                continue

            # Log the search parameters
            _logger.debug(f"Searching stock.quan with product_id={record.product_id.id} "
                         f"and location_id={record.source_location_id.id}")

            stock_quants = self.env['stock.quan'].search([
                ('product_id', '=', record.product_id.id),
                ('location_id', '=', record.source_location_id.id)
            ])

            # Log the search results
            _logger.debug(f"Found {len(stock_quants)} stock quants")

            if stock_quants:
                total_quantity = sum(stock_quants.mapped('quantity'))
                _logger.debug(f"Total quantity found: {total_quantity}")
                record.max_quantity = total_quantity
            else:
                _logger.warning(
                    f"No stock quant found for product {record.product_id.name} "
                    f"in location {record.source_location_id.name}"
                )

    @api.constrains('quantity')
    def _check_quantity(self):
        """
        Ensure the quantity does not exceed the maximum available quantity.
        """
        for record in self:
            # Force recompute max_quantity
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
            """
            Validate the stock movement by updating source and destination stock quantities.
            """
            self.ensure_one()
            try:
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

                # Update source stock
                source_stock_line.quantity -= self.quantity

                # Update or create destination stock
                dest_stock_line = self.env['stock.quan'].search([
                    ('product_id', '=', self.product_id.id),
                    ('location_id', '=', self.destination_location_id.id)
                ], limit=1)

                if dest_stock_line:
                    dest_stock_line.quantity += self.quantity
                else:
                    self.env['stock.quan'].create({
                        'product_id': self.product_id.id,
                        'location_id': self.destination_location_id.id,
                        'quantity': self.quantity,
                    })

                _logger.info(
                    f"Validated stock movement: {self.quantity} units of {self.product_id.name} "
                    f"from {self.source_location_id.name} to {self.destination_location_id.name}"
                )
            except Exception as e:
                self.env.cr.rollback()
                _logger.error(f"Error during stock movement validation: {str(e)}")
                raise exceptions.UserError(
                    f"Une erreur s'est produite lors de la validation du mouvement: {str(e)}"
                )

    def write(self, vals):
        """
        Override write method to control state transitions.
        """
        if 'state' in vals:
            for record in self:
                if record.state == 'done' and vals['state'] != 'done':
                    raise exceptions.UserError(
                        "Impossible de modifier l'état d'un mouvement validé."
                    )

                if vals['state'] == 'done' and record.state == 'draft':
                    record._validate_movement()

                if vals['state'] == 'cancelled' and record.state != 'draft':
                    raise exceptions.UserError(
                        "Seuls les mouvements en brouillon peuvent être annulés."
                    )

        return super(StockMovement, self).write(vals)