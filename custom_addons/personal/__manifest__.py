# -*- coding: utf-8 -*-
{
    "name": "Personal Habits, Journal & Vision",
    "version": "18.0.1.0.0",
    "summary": "Aesthetic habit tracker, journaling and vision board (mobile-first)",
    "description": """
Personal Productivity Suite
===========================
A beautiful personal productivity module featuring:
- **Habit Tracker**: Track daily habits with streaks, colors, and quick check-ins
- **Journal**: Rich journaling with mood tracking and emojis
- **Vision Board**: Pinterest-style vision board with images

Mobile-first design with aesthetic UI components.
    """,
    "category": "Productivity",
    "author": "Piyush",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/personal_record_rules.xml",
        "views/personal_menus.xml",
        "views/habit_entry_views.xml",
        "views/habit_views.xml",
        "views/journal_views.xml",
        "views/vision_views.xml",
        "data/cron_recompute_streaks.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
