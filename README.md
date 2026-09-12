# SpeisePlan for Home Assistant

Brings your [SpeisePlan](https://github.com/ajfriesen/SpeisePlan) meal plan into Home
Assistant, so you can put it on a dashboard or render it onto an e-paper display.

For every day in the plan you get the meal's **name**, the **link** to the recipe, and
the **photo**.

## Entities

One device, with the following entities.

| Entity | State | Notes |
| --- | --- | --- |
| `sensor.speiseplan_today` | Name of the first meal planned for today | `unknown` when nothing is planned |
| `sensor.speiseplan_day_1` … `day_6` | Same, for the next six days | `day_1` is tomorrow |
| `sensor.speiseplan_meal_plan` | Number of meals planned in the window | Carries the whole plan in attributes |
| `sensor.speiseplan_unassigned` | Number of meals staged without a day | |
| `image.speiseplan_today`, `image.speiseplan_day_1` | The meal's photo | |
| `image.speiseplan_day_2` … `day_6` | Same | Disabled by default — see below |

### Day sensor attributes

Every attribute is always present, so templates never need a guard:

```yaml
date: "2026-09-14"
weekday: Monday
offset: 2
meal_count: 1
has_meal: true
meals:                       # every meal planned that day, in order
  - name: Lasagne
    url: https://example.com/lasagne
    photo_url: /api/v1/recipes/7/photo
    minutes: 45
    tag: pasta
    recipe_id: 7
    day: "2026-09-14"
name: Lasagne                # convenience copies of meals[0]
url: https://example.com/lasagne
photo_url: /api/v1/recipes/7/photo
minutes: 45
tag: pasta
recipe_id: 7
image_entity_id: image.speiseplan_day_2
```

A day can hold **more than one meal** — SpeisePlan has no breakfast/lunch/dinner slots.
The state shows the first one; `meals` has them all.

`sensor.speiseplan_meal_plan` additionally carries `meals` (every assigned meal, flat)
and `days` (the same grouped per day), which is handy when one template renders the
whole week.

None of these attributes are written to the recorder — they would blow past its 16 KiB
per-row limit and be silently dropped, and there is nothing in them worth graphing.

### Why most image entities are disabled

Home Assistant rewrites every image entity's state every five minutes to rotate its
access token, whether or not the picture changed. Seven always-on image entities would
add roughly 2000 state changes a day. Today and tomorrow are enabled; enable the rest in
the entity settings if you need them.

## Getting the photo onto a display

`entity_picture` looks like a URL you can hand to a display, but **its `?token=` expires
after about ten minutes**. Never bake one into a device config. Pick whichever of these
fits your setup:

**1. Rendering inside Home Assistant** (OpenEPaperLink `drawcustom`, `dlimg`, …) — use a
template, which is re-evaluated with a fresh token each render:

```yaml
- type: dlimg
  url: "{{ state_attr('image.speiseplan_today', 'entity_picture') }}"
  x: 0
  y: 0
  xsize: 296
  ysize: 128
- type: text
  value: "{{ states('sensor.speiseplan_today') }}"
  x: 0
  y: 132
  size: 20
```

**2. An external renderer** — fetch the image proxy with a long-lived access token. This
URL is stable forever:

```bash
curl -H "Authorization: Bearer <HA long-lived access token>" \
     http://homeassistant.local:8123/api/image_proxy/image.speiseplan_today \
     -o today.png
```

**3. A renderer that can reach SpeisePlan directly** — join the day sensor's `photo_url`
onto your SpeisePlan address and send the SpeisePlan API token:

```bash
curl -H "Authorization: Bearer <SpeisePlan API token>" \
     "http://speiseplan.local:8080/api/v1/recipes/7/photo"
```

SpeisePlan serves both locally stored and externally hosted photos from that one
endpoint, so your renderer never has to care which kind a recipe has.

### Whole-week template

```jinja
{% for day in state_attr('sensor.speiseplan_meal_plan', 'days') %}
{{ day.weekday[:3] }} {{ day.date[-5:] }}  {{ day.meals | map(attribute='name') | join(', ') or '—' }}
{% endfor %}
```

## Installation

### HACS

Add this repository as a custom repository (category: Integration), install SpeisePlan,
and restart Home Assistant.

### Manual

Copy `custom_components/speiseplan` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration

Open **Settings → Devices & services → Add integration → SpeisePlan** and enter:

| Field | Value |
| --- | --- |
| Host | Where SpeisePlan runs. For the add-on this is the add-on hostname shown on its Info page, or your Home Assistant host's address. |
| Port | `8080` by default |
| API token | From SpeisePlan's **Settings** page (`http://<speiseplan>/settings`) |
| Uses HTTPS | Only if you put SpeisePlan behind a TLS reverse proxy |

SpeisePlan generates an API token on first start; you can also pin your own with the
`SPEISEPLAN_API_TOKEN` environment variable or the add-on's `api_token` option. Either
way the current value is shown on the Settings page.

Requires a SpeisePlan new enough to serve `/api/v1` — older versions have no API and the
config flow will say so.

### Time zones

"Today" is whatever SpeisePlan says it is. If SpeisePlan and Home Assistant run in
different time zones the integration logs a warning at startup, because the day entities
follow SpeisePlan's calendar, not Home Assistant's.

### If the entities ever come back as a new device

The integration identifies your SpeisePlan by an instance ID stored in its database. If
you restore SpeisePlan from a backup with a different database, that ID changes and Home
Assistant treats it as a new device. The ID is shown on SpeisePlan's Settings page.

## Development

```bash
nix develop          # commitizen + ruff
ruff check custom_components/
ruff format custom_components/
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/); releases are
cut by release-please, which also bumps `manifest.json`.
