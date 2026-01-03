# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta, date


class PersonalHabit(models.Model):
    _name = "personal.habit"
    _description = "Habit (definition)"
    _order = "sequence, id desc"

    name = fields.Char(required=True, string="Habit Name")
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        required=True,
        default=lambda self: self.env.user.id
    )
    sequence = fields.Integer(default=10)
    
    # Visual/Aesthetic fields
    icon = fields.Char(string="Emoji Icon", default="✨", help="Emoji to represent this habit")
    color_code = fields.Selection([
        ('purple', '💜 Purple'),
        ('blue', '💙 Blue'),
        ('green', '💚 Green'),
        ('yellow', '💛 Yellow'),
        ('orange', '🧡 Orange'),
        ('red', '❤️ Red'),
        ('pink', '🩷 Pink'),
        ('teal', '🩵 Teal'),
    ], default='purple', string="Color Theme")
    color = fields.Integer(compute='_compute_color', store=True)
    
    # Frequency settings
    frequency_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekdays', 'Weekdays (Mon-Fri)'),
        ('every_n_days', 'Every N days'),
        ('custom', 'Custom days'),
    ], default='daily', required=True, string="Frequency")
    every_n_days = fields.Integer(default=1, string="Every N Days")
    custom_days = fields.Char(
        help='CSV of weekday numbers 0=Mon..6=Sun (e.g., "0,2,4" for Mon, Wed, Fri)'
    )
    goal = fields.Integer(default=1, string="Daily Goal")
    
    # Streak tracking
    current_streak = fields.Integer(default=0, store=True, string="Current Streak 🔥")
    longest_streak = fields.Integer(default=0, store=True, string="Longest Streak")
    last_done_date = fields.Date(string="Last Completed")
    
    # Computed fields
    entry_count = fields.Integer(compute='_compute_entry_count', string="Total Check-ins")
    today_done = fields.Boolean(compute='_compute_today_done', string="Done Today")
    completion_rate = fields.Float(compute='_compute_completion_rate', string="30-Day Rate %")
    
    entry_ids = fields.One2many('personal.habit.entry', 'habit_id', string="Entries")

    @api.depends('color_code')
    def _compute_color(self):
        """Map color_code to Odoo's integer color index for kanban"""
        color_map = {
            'purple': 9,
            'blue': 4,
            'green': 10,
            'yellow': 3,
            'orange': 2,
            'red': 1,
            'pink': 6,
            'teal': 5,
        }
        for rec in self:
            rec.color = color_map.get(rec.color_code, 0)

    def _compute_entry_count(self):
        for rec in self:
            rec.entry_count = self.env['personal.habit.entry'].search_count([
                ('habit_id', '=', rec.id)
            ])

    def _compute_today_done(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.today_done = bool(self.env['personal.habit.entry'].search([
                ('habit_id', '=', rec.id),
                ('date', '=', today),
                ('success', '=', True)
            ], limit=1))

    def _compute_completion_rate(self):
        """Calculate completion rate for last 30 days"""
        today = fields.Date.context_today(self)
        thirty_days_ago = today - timedelta(days=30)
        for rec in self:
            # Count expected days based on frequency
            expected_days = rec._count_expected_days(thirty_days_ago, today)
            if expected_days == 0:
                rec.completion_rate = 0.0
                continue
            actual_entries = self.env['personal.habit.entry'].search_count([
                ('habit_id', '=', rec.id),
                ('date', '>=', thirty_days_ago),
                ('date', '<=', today),
                ('success', '=', True)
            ])
            rec.completion_rate = min(100.0, (actual_entries / expected_days) * 100)

    def _count_expected_days(self, start_date, end_date):
        """Count how many days the habit should have been done"""
        if self.frequency_type == 'daily':
            return (end_date - start_date).days + 1
        elif self.frequency_type == 'weekdays':
            count = 0
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:  # Mon-Fri
                    count += 1
                current += timedelta(days=1)
            return count
        elif self.frequency_type == 'every_n_days':
            days = self.every_n_days or 1
            return max(1, ((end_date - start_date).days + 1) // days)
        elif self.frequency_type == 'custom':
            if not self.custom_days:
                return (end_date - start_date).days + 1
            allowed = [int(x) for x in self.custom_days.split(',') if x.strip().isdigit()]
            count = 0
            current = start_date
            while current <= end_date:
                if current.weekday() in allowed:
                    count += 1
                current += timedelta(days=1)
            return count
        return (end_date - start_date).days + 1

    def _expected_next_date(self, prev_date):
        """Calculate expected next date based on frequency"""
        if self.frequency_type == 'daily':
            return prev_date + timedelta(days=1)
        if self.frequency_type == 'every_n_days':
            days = self.every_n_days or 1
            return prev_date + timedelta(days=days)
        if self.frequency_type == 'weekdays':
            nxt = prev_date + timedelta(days=1)
            while nxt.weekday() >= 5:  # 5=Sat, 6=Sun
                nxt += timedelta(days=1)
            return nxt
        if self.frequency_type == 'custom':
            if not self.custom_days:
                return prev_date + timedelta(days=1)
            allowed = [int(x) for x in self.custom_days.split(',') if x.strip().isdigit()]
            nxt = prev_date + timedelta(days=1)
            for _ in range(7):  # Max 7 days to find next
                if nxt.weekday() in allowed:
                    return nxt
                nxt += timedelta(days=1)
            return nxt
        return prev_date + timedelta(days=1)

    def recompute_streak(self):
        """Recompute current and longest streak for habits"""
        Entry = self.env['personal.habit.entry']
        for habit in self:
            entries = Entry.search([
                ('habit_id', '=', habit.id),
                ('success', '=', True)
            ], order='date asc')
            
            cur = 0
            longest = 0
            prev_date = None
            
            for e in entries:
                e_date = e.date
                if isinstance(e_date, str):
                    e_date = fields.Date.from_string(e_date)
                
                if prev_date is None:
                    cur = 1
                else:
                    expected = habit._expected_next_date(prev_date)
                    if e_date == expected:
                        cur += 1
                    elif e_date > expected:
                        cur = 1
                    else:
                        cur = 1
                
                if cur > longest:
                    longest = cur
                prev_date = e_date
            
            habit.current_streak = cur
            habit.longest_streak = max(habit.longest_streak or 0, longest)
            if prev_date:
                habit.last_done_date = prev_date

    def action_check_today(self):
        """Quick action to mark habit as done for today"""
        self.ensure_one()
        today = fields.Date.context_today(self)
        Entry = self.env['personal.habit.entry']
        
        existing = Entry.search([
            ('habit_id', '=', self.id),
            ('date', '=', today)
        ], limit=1)
        
        if existing:
            # Toggle success status
            existing.success = not existing.success
        else:
            # Create new entry
            Entry.create({
                'habit_id': self.id,
                'date': today,
                'success': True,
                'user_id': self.env.user.id,
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
