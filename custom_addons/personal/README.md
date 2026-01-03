# Personal Productivity Suite 🎯📔🌟

A beautiful, mobile-first personal productivity module for Odoo 18 featuring:

## Features

### 🎯 Habit Tracker
- **Visual Habits**: Emoji icons and color themes for each habit
- **Streak Tracking**: Current and longest streak with 🔥 indicators
- **Quick Check-in**: One-tap "Check Today" button on kanban cards
- **Flexible Frequency**: Daily, weekdays, every N days, or custom days
- **30-Day Completion Rate**: Progress bar showing consistency
- **Calendar View**: Visualize your check-ins over time

### 📔 Journal
- **Mood Tracking**: 5-level mood with emoji visualization (😄😊😐😔😢)
- **Rich Content**: HTML editor for beautiful journal entries
- **Tags**: Organize entries with colored tags
- **Calendar View**: See your journaling patterns
- **Kanban & List Views**: Multiple ways to browse entries

### 🌟 Vision Board
- **Pinterest-Style**: Large image previews in kanban view
- **Goal Tracking**: Target dates and achievement status
- **Drag & Drop**: Reorder your visions by priority
- **Categories**: Organize visions (Career, Health, Travel, etc.)
- **Achievement Badges**: Celebrate when you achieve a vision! 🎉

## Installation

1. Place this module in your Odoo `custom_addons` directory
2. Restart Odoo server
3. Update Apps List: Apps → Update Apps List
4. Search for "Personal" and install

## Security

- All data is private to each user
- Record rules ensure users only see their own data
- Full CRUD permissions for internal users

## Cron Jobs

- **Daily Streak Recompute**: Automatically recalculates all habit streaks at midnight

## Technical

- **Odoo Version**: 18.0
- **Dependencies**: base, mail
- **License**: LGPL-3
