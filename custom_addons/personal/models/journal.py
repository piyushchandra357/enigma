# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PersonalJournal(models.Model):
    _name = "personal.journal"
    _description = "Journal Entry"
    _order = "date desc, id desc"

    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user.id,
        required=True,
        string="Author"
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
        string="Date & Time"
    )
    title = fields.Char(string="Title")
    content = fields.Html(string="Content")
    
    # Enhanced mood with emojis
    mood = fields.Selection([
        ('5', '😄 Amazing'),
        ('4', '🙂 Good'),
        ('3', '😐 Neutral'),
        ('2', '😔 Bad'),
        ('1', '😢 Terrible'),
    ], string="Mood")
    
    mood_emoji = fields.Char(compute='_compute_mood_emoji', string="Mood Emoji")
    
    # Tags for organization
    tag_ids = fields.Many2many(
        'personal.journal.tag',
        string="Tags"
    )
    
    # Preview for kanban
    content_preview = fields.Char(compute='_compute_content_preview', string="Preview")
    color = fields.Integer(default=0)

    @api.depends('mood')
    def _compute_mood_emoji(self):
        emoji_map = {
            '5': '😄',
            '4': '🙂',
            '3': '😐',
            '2': '😔',
            '1': '😢',
        }
        for rec in self:
            rec.mood_emoji = emoji_map.get(rec.mood, '📝')

    @api.depends('content')
    def _compute_content_preview(self):
        import re
        for rec in self:
            if rec.content:
                # Strip HTML tags and truncate
                clean = re.sub('<[^<]+?>', '', rec.content or '')
                rec.content_preview = clean[:100] + '...' if len(clean) > 100 else clean
            else:
                rec.content_preview = ''


class PersonalJournalTag(models.Model):
    _name = "personal.journal.tag"
    _description = "Journal Tag"

    name = fields.Char(required=True, string="Tag Name")
    color = fields.Integer(default=0)
