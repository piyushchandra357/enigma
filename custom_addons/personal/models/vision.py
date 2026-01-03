# -*- coding: utf-8 -*-
from odoo import models, fields


class PersonalVision(models.Model):
    _name = "personal.vision"
    _description = "Vision Board Item"
    _order = "sequence, id desc"

    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user.id,
        required=True,
        string="Owner"
    )
    title = fields.Char(required=True, string="Vision Title")
    description = fields.Text(string="Description")
    
    # Image field - using image_1920 for optimized handling
    image_1920 = fields.Image(
        string="Image",
        max_width=1920,
        max_height=1920
    )
    image_256 = fields.Image(
        string="Thumbnail",
        related="image_1920",
        max_width=256,
        max_height=256,
        store=True
    )
    
    # Additional attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments'
    )
    
    sequence = fields.Integer(default=10, string="Order")
    category = fields.Char(string="Category")
    
    # For kanban grouping/coloring
    color = fields.Integer(default=0)
    
    # Goal tracking
    target_date = fields.Date(string="Target Date")
    is_achieved = fields.Boolean(default=False, string="Achieved 🎉")
