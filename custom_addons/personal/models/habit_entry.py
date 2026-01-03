# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PersonalHabitEntry(models.Model):
    _name = "personal.habit.entry"
    _description = "Habit Check-in Entry"
    _order = "date desc, id desc"

    habit_id = fields.Many2one(
        'personal.habit',
        string="Habit",
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        required=True,
        default=lambda self: self.env.user.id
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        index=True,
        string="Date"
    )
    note = fields.Text(string="Notes")
    success = fields.Boolean(default=True, string="Completed")
    
    # Related fields for display
    habit_name = fields.Char(related='habit_id.name', string="Habit Name", store=True)
    habit_icon = fields.Char(related='habit_id.icon', string="Icon")

    _sql_constraints = [
        ('one_entry_per_day', 'unique(habit_id, date)',
         'Only one entry per habit per date is allowed.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Recompute streaks for affected habits
        habits = records.mapped('habit_id')
        for habit in habits:
            try:
                habit.recompute_streak()
            except Exception:
                pass  # Don't break creation if recompute fails
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'success' in vals or 'date' in vals:
            habits = self.mapped('habit_id')
            for habit in habits:
                try:
                    habit.recompute_streak()
                except Exception:
                    pass
        return res

    def unlink(self):
        habits = self.mapped('habit_id')
        res = super().unlink()
        for habit in habits:
            try:
                habit.recompute_streak()
            except Exception:
                pass
        return res
