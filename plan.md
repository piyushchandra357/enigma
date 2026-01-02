# Folder layout (one top-level module `personal` — split later if you want)

```text
custom_addons/personal/
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── habit.py
│   ├── habit_entry.py
│   ├── journal.py
│   └── vision.py
├── views/
│   ├── personal_menus.xml
│   ├── habit_views.xml
│   ├── habit_entry_views.xml
│   ├── journal_views.xml
│   └── vision_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── personal_record_rules.xml
├── data/
│   └── cron_recompute_streaks.xml
└── README.md
```

---

# `__manifest__.py` (module metadata)

```python
{
    "name": "Personal Habits, Journal & Vision",
    "version": "0.1",
    "summary": "Habit tracker, journaling and vision board (mobile-first)",
    "description": "Personal productivity modules: habits, habit entries, journals, vision items.",
    "category": "Tools",
    "author": "You",
    "license": "LGPL-3",
    "depends": ["base", "mail"],   # mail optional, keeps chatter if you want
    "data": [
        "security/ir.model.access.csv",
        "security/personal_record_rules.xml",
        "views/personal_menus.xml",
        "views/habit_views.xml",
        "views/habit_entry_views.xml",
        "views/journal_views.xml",
        "views/vision_views.xml",
        "data/cron_recompute_streaks.xml",
    ],
    "installable": True,
    "application": True,
}
```

---

# Models — Python (Odoo 18 style)

### `models/__init__.py`

```python
from . import habit
from . import habit_entry
from . import journal
from . import vision
```

---

### `models/habit.py`

```python
from odoo import models, fields, api
from datetime import timedelta, date

class PersonalHabit(models.Model):
    _name = "personal.habit"
    _description = "Habit (definition)"
    _order = "id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Owner', required=True, default=lambda self: self.env.user.id)
    frequency_type = fields.Selection([
        ('daily','Daily'),
        ('weekdays','Weekdays (Mon-Fri)'),
        ('every_n_days','Every N days'),
        ('custom','Custom days'),
    ], default='daily', required=True)
    every_n_days = fields.Integer(default=1)
    custom_days = fields.Char(help='CSV of weekday numbers 0=Mon..6=Sun')  # "0,2,4"
    goal = fields.Integer(default=1)
    current_streak = fields.Integer(default=0, store=True)
    longest_streak = fields.Integer(default=0, store=True)
    last_done_date = fields.Date()
    color = fields.Integer()
    created_count = fields.Integer(compute='_compute_created_count')

    def _compute_created_count(self):
        for rec in self:
            rec.created_count = self.env['personal.habit.entry'].search_count([('habit_id','=',rec.id)])

    def _expected_next_date(self, habit, prev_date):
        # prev_date: date object
        if habit.frequency_type == 'daily':
            return prev_date + timedelta(days=1)
        if habit.frequency_type == 'every_n_days':
            days = habit.every_n_days or 1
            return prev_date + timedelta(days=days)
        if habit.frequency_type == 'weekdays':
            nxt = prev_date + timedelta(days=1)
            while nxt.weekday() >= 5:  # 5=Sat,6=Sun
                nxt += timedelta(days=1)
            return nxt
        if habit.frequency_type == 'custom':
            if not habit.custom_days:
                return prev_date + timedelta(days=1)
            allowed = [int(x) for x in habit.custom_days.split(',') if x.strip().isdigit()]
            nxt = prev_date + timedelta(days=1)
            while nxt.weekday() not in allowed:
                nxt += timedelta(days=1)
            return nxt
        return prev_date + timedelta(days=1)

    def recompute_streak(self):
        Entry = self.env['personal.habit.entry']
        for habit in self:
            entries = Entry.search([('habit_id','=',habit.id),('success','=',True)], order='date asc')
            cur = 0
            longest = 0
            prev_date = None
            for e in entries:
                e_date = fields.Date.from_string(e.date)
                if prev_date is None:
                    cur = 1
                else:
                    expected = self._expected_next_date(habit, prev_date)
                    # compare dates exactly
                    if e_date == expected:
                        cur += 1
                    elif e_date > expected:
                        cur = 1
                    else:
                        # backfill older date (shouldn't happen with ascending order)
                        cur = 1
                if cur > longest:
                    longest = cur
                prev_date = e_date
            habit.current_streak = cur
            # longest_streak should be the max historically
            habit.longest_streak = max(habit.longest_streak or 0, longest)
            habit.last_done_date = fields.Date.to_string(prev_date) if prev_date else habit.last_done_date
```

Notes on streak code:

* Uses `fields.Date.from_string`/`to_string` to convert between Odoo date strings and `datetime.date`.
* The recompute scans all successful entries ordered by date (cheap for personal datasets). If you later need performance you can fetch last N entries.

---

### `models/habit_entry.py`

```python
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PersonalHabitEntry(models.Model):
    _name = "personal.habit.entry"
    _description = "Single habit occurrence"
    _order = "date desc"

    habit_id = fields.Many2one('personal.habit', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Owner', required=True, default=lambda self: self.env.user.id)
    date = fields.Date(default=fields.Date.context_today, required=True, index=True)
    note = fields.Text()
    success = fields.Boolean(default=True)

    _sql_constraints = [
        ('one_entry_per_day', 'unique(habit_id, date)', 'Only one entry per habit per date is allowed.')
    ]

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Recompute streaks for that habit
        try:
            rec.habit_id.recompute_streak()
        except Exception:
            # do not break creation if recompute fails
            pass
        return rec

    def unlink(self):
        habits = self.mapped('habit_id')
        res = super().unlink()
        try:
            for h in habits:
                h.recompute_streak()
        except Exception:
            pass
        return res
```

Notes:

* `create` and `unlink` trigger a recompute — keeps stored `current_streak`/`longest_streak` consistent.
* The SQL unique constraint prevents duplicate same-day entries.

---

### `models/journal.py`

```python
from odoo import models, fields

class PersonalJournal(models.Model):
    _name = "personal.journal"
    _description = "Journal entry"

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, required=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    title = fields.Char()
    content = fields.Html()
    mood = fields.Selection([('v','Very good'),('g','Good'),('n','Neutral'),('b','Bad')])
```

---

### `models/vision.py`

```python
from odoo import models, fields

class PersonalVision(models.Model):
    _name = "personal.vision"
    _description = "Vision board item"

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, required=True)
    title = fields.Char(required=True)
    description = fields.Text()
    image = fields.Binary(attachment=False)   # small inline preview
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    sequence = fields.Integer(default=10)
    category = fields.Char()
```

Notes:

* For large images use `ir.attachment` (binary field with `attachment=True` or create attachments via `ir.attachment.create`).

---

# Views (XML) — mobile friendly

### `views/personal_menus.xml`

```xml
<odoo>
  <menuitem id="menu_personal_root" name="Personal" sequence="90"/>
  <menuitem id="menu_personal_habits" name="Habits" parent="menu_personal_root" sequence="1"/>
  <menuitem id="menu_personal_journals" name="Journals" parent="menu_personal_root" sequence="2"/>
  <menuitem id="menu_personal_vision" name="Vision Board" parent="menu_personal_root" sequence="3"/>
</odoo>
```

---

### `views/habit_views.xml` (list + form)

```xml
<odoo>
  <record id="view_personal_habit_tree" model="ir.ui.view">
    <field name="name">personal.habit.tree</field>
    <field name="model">personal.habit</field>
    <field name="arch" type="xml">
      <tree>
        <field name="name"/>
        <field name="current_streak"/>
        <field name="last_done_date"/>
        <field name="goal"/>
      </tree>
    </field>
  </record>

  <record id="view_personal_habit_form" model="ir.ui.view">
    <field name="name">personal.habit.form</field>
    <field name="model">personal.habit</field>
    <field name="arch" type="xml">
      <form>
        <sheet>
          <group>
            <field name="name"/>
            <field name="active"/>
            <field name="frequency_type"/>
            <field name="every_n_days" attrs="{'invisible':[('frequency_type','!=','every_n_days')]}"/>
            <field name="custom_days" attrs="{'invisible':[('frequency_type','!=','custom')]}"/>
            <field name="goal"/>
          </group>
          <group>
            <field name="current_streak" readonly="1"/>
            <field name="longest_streak" readonly="1"/>
            <field name="last_done_date" readonly="1"/>
          </group>
        </sheet>
      </form>
    </field>
  </record>

  <record id="action_personal_habit" model="ir.actions.act_window">
    <field name="name">Habits</field>
    <field name="res_model">personal.habit</field>
    <field name="view_mode">kanban,tree,form</field>
    <field name="help" type="html">
      <p class="oe_view_nocontent_create">Create your first habit.</p>
    </field>
  </record>

  <menuitem id="menu_personal_habit_action" name="Manage Habits" parent="menu_personal_habits" action="action_personal_habit"/>
</odoo>
```

Notes:

* Kanban can be added with a custom template for image/streak display to be mobile-friendly.

---

### `views/habit_entry_views.xml`

```xml
<odoo>
  <record id="view_personal_habit_entry_tree" model="ir.ui.view">
    <field name="name">personal.habit.entry.tree</field>
    <field name="model">personal.habit.entry</field>
    <field name="arch" type="xml">
      <tree>
        <field name="habit_id"/>
        <field name="date"/>
        <field name="note"/>
        <field name="success"/>
      </tree>
    </field>
  </record>

  <record id="view_personal_habit_entry_form" model="ir.ui.view">
    <field name="name">personal.habit.entry.form</field>
    <field name="model">personal.habit.entry</field>
    <field name="arch" type="xml">
      <form>
        <sheet>
          <group>
            <field name="habit_id"/>
            <field name="date"/>
            <field name="success"/>
            <field name="note"/>
          </group>
        </sheet>
      </form>
    </field>
  </record>

  <record id="action_personal_habit_entry" model="ir.actions.act_window">
    <field name="name">Habit Entries</field>
    <field name="res_model">personal.habit.entry</field>
    <field name="view_mode">tree,form</field>
  </record>

  <menuitem id="menu_personal_habit_entry_action" name="Check-ins" parent="menu_personal_habits" action="action_personal_habit_entry"/>
</odoo>
```

---

### `views/journal_views.xml`

```xml
<odoo>
  <record id="view_personal_journal_tree" model="ir.ui.view">
    <field name="name">personal.journal.tree</field>
    <field name="model">personal.journal</field>
    <field name="arch" type="xml">
      <tree>
        <field name="date"/>
        <field name="title"/>
        <field name="mood"/>
      </tree>
    </field>
  </record>

  <record id="view_personal_journal_form" model="ir.ui.view">
    <field name="name">personal.journal.form</field>
    <field name="model">personal.journal</field>
    <field name="arch" type="xml">
      <form>
        <sheet>
          <group>
            <field name="title"/>
            <field name="date"/>
            <field name="mood"/>
          </group>
          <group>
            <field name="content" widget="html"/>
          </group>
        </sheet>
      </form>
    </field>
  </record>

  <record id="action_personal_journal" model="ir.actions.act_window">
    <field name="name">Journals</field>
    <field name="res_model">personal.journal</field>
    <field name="view_mode">kanban,tree,form</field>
  </record>

  <menuitem id="menu_personal_journal_action" name="My Journal" parent="menu_personal_journals" action="action_personal_journal"/>
</odoo>
```

---

### `views/vision_views.xml` (kanban)

```xml
<odoo>
  <record id="view_personal_vision_kanban" model="ir.ui.view">
    <field name="name">personal.vision.kanban</field>
    <field name="model">personal.vision</field>
    <field name="arch" type="xml">
      <kanban>
        <templates>
          <t t-name="kanban-box">
            <div class="oe_kanban_card o_kanban_record">
              <div class="o_kanban_record_image">
                <img t-if="record.image.raw_value" t-att-src="'data:image/png;base64,%s' % record.image.raw_value"/>
              </div>
              <div class="o_kanban_record_body">
                <field name="title"/>
                <field name="description"/>
              </div>
            </div>
          </t>
        </templates>
      </kanban>
    </field>
  </record>

  <record id="action_personal_vision" model="ir.actions.act_window">
    <field name="name">Vision Board</field>
    <field name="res_model">personal.vision</field>
    <field name="view_mode">kanban,form</field>
  </record>

  <menuitem id="menu_personal_vision_action" name="Board" parent="menu_personal_vision" action="action_personal_vision"/>
</odoo>
```

---

# Security — `ir.model.access.csv` example

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_personal_habit,access_personal_habit,model_personal_habit,base.group_user,1,1,1,1
access_personal_habit_entry,access_personal_habit_entry,model_personal_habit_entry,base.group_user,1,1,1,1
access_personal_journal,access_personal_journal,model_personal_journal,base.group_user,1,1,1,1
access_personal_vision,access_personal_vision,model_personal_vision,base.group_user,1,1,1,1
```

---

# Record rules — `security/personal_record_rules.xml`

```xml
<odoo>
  <record id="rule_personal_habit_user" model="ir.rule">
    <field name="name">personal.habit: own records</field>
    <field name="model_id" ref="model_personal_habit"/>
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
  </record>

  <record id="rule_personal_habit_entry_user" model="ir.rule">
    <field name="name">personal.habit.entry: own records</field>
    <field name="model_id" ref="model_personal_habit_entry"/>
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
  </record>

  <record id="rule_personal_journal_user" model="ir.rule">
    <field name="name">personal.journal: own records</field>
    <field name="model_id" ref="model_personal_journal"/>
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
  </record>

  <record id="rule_personal_vision_user" model="ir.rule">
    <field name="name">personal.vision: own records</field>
    <field name="model_id" ref="model_personal_vision"/>
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
  </record>
</odoo>
```

---

# Scheduled job (cron) — `data/cron_recompute_streaks.xml`

```xml
<odoo>
  <record id="ir_cron_recompute_habit_streaks" model="ir.cron">
    <field name="name">Recompute habit streaks</field>
    <field name="model_id" ref="model_personal_habit"/>
    <field name="state">code</field>
    <field name="code">model.recompute_streak()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="numbercall">-1</field>
    <field name="doall" eval="False"/>
  </record>
</odoo>
```

Note: Odoo cron `state='code'` executes Python expression in `code` — this is standard for scheduled actions.

---

# Helpful extras (quick actions & server controllers)

If you want a simple API for mobile or a faster “check today” button, add a small controller:

```python
from odoo import http
class PersonalController(http.Controller):
    @http.route('/personal/api/habits/today', type='json', auth='user', cors='*')
    def api_habits_today(self):
        user = http.request.env.user
        Habit = http.request.env['personal.habit'].sudo().search([('user_id','=',user.id),('active','=',True)])
        res = []
        for h in Habit:
            res.append({
                'id': h.id,
                'name': h.name,
                'current_streak': h.current_streak,
                'last_done_date': h.last_done_date,
            })
        return res
```

This is optional but convenient if you later want a custom mobile frontend.

---

# Deployment checklist for **Skysize + Odoo 18**

(Assuming Skysize provides an Odoo hosting service or a VPS-like environment — steps are generic and Odoo-specific)

1. **Place module** in `addons_path` (e.g., `/mnt/extra-addons/personal/`) on your Skysize Odoo instance.
2. **Restart Odoo service** so the addons directory is rescanned.
3. In Odoo UI: **Update Apps list** (Apps → Update Apps List).
4. Install the **Personal** module.
5. **Set filestore persistence**: ensure `filestore` is on a persistent disk (Skysize should have persistent volumes). Attachments and `ir.attachment` require correct permissions and persistence.
6. **Database backup**: set up a nightly `pg_dump` to another persistent volume or remote storage. Skysize may offer DB backups; enable them.
7. **Workers & Longpolling**: for small single-user setups, `workers = 0` (all in threaded mode) may be okay. For any background tasks or if you use longpolling, configure `workers > 0` and set up a separate longpolling service (`--longpolling-port`) per Odoo docs.
8. **Reverse proxy & SSL**: configure Nginx/Traefik on Skysize or use Skysize's managed TLS to front Odoo on port 8069. Always use HTTPS.
9. **System users & permissions**: ensure Odoo process user has write access to `filestore` and log directories.
10. **Cron & alarms**: verify `ir.cron` runs (Odoo scheduler) — Skysize managed Odoo typically has this enabled.
11. **Monitoring**: enable logs and alerts. Keep an eye on memory; add swap if needed for small instances.
12. **Access control**: ensure only intended users (≤3) have accounts; keep admin user credentials safe.

---

# Mobile UI & UX recommendations (Odoo-specific)

* Use **single-column forms**: Odoo `sheet` + `group` will adapt, but for mobile prefer `<group col="1">`.
* **Large tappable elements**: use kanban with large cards and a custom `kanban-box` template that uses buttons for "Mark done".
* **Quick add**: create an `action` on the habit list to create a habit entry for "today" (server action or button).
* **Minimize heavy lists**: default list page shows last 7 days, full history behind "View history".
* **Image handling**: use small binary thumbnails in kanban; upload attachments to `ir.attachment` so Odoo serves them efficiently.
* **Performance**: keep views lightweight; avoid loading many `one2many` lines on initial screen.

---
