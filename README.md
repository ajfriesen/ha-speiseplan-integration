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

There are no image entities: the photo is a URL on the day sensor, which whatever draws
your display fetches itself. See [Getting the photo onto a
display](#getting-the-photo-onto-a-display).

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
    photo_url: http://49e94de4-speiseplan:8080/api/v1/recipes/7/photo
    has_photo: true
    minutes: 45
    tag: pasta
    recipe_id: 7
    day: "2026-09-14"
name: Lasagne                # convenience copies of meals[0]
url: https://example.com/lasagne
photo_url: http://49e94de4-speiseplan:8080/api/v1/recipes/7/photo
has_photo: true
minutes: 45
tag: pasta
recipe_id: 7
```

A day can hold **more than one meal** — SpeisePlan has no breakfast/lunch/dinner slots.
The state shows the first one; `meals` has them all.

`sensor.speiseplan_meal_plan` additionally carries `meals` (every assigned meal, flat)
and `days` (the same grouped per day), which is handy when one template renders the
whole week.

None of these attributes are written to the recorder — they would blow past its 16 KiB
per-row limit and be silently dropped, and there is nothing in them worth graphing.

## Getting the photo onto a display

`photo_url` is an absolute URL pointing straight at SpeisePlan, so a renderer can fetch
it directly — no Home Assistant image proxy, no expiring token, nothing cached in
between.

With [OpenDisplay](https://opendisplay.org), template it into a `dlimg` element. The
renderer runs inside Home Assistant, which is what makes this work: it can reach the
add-on's internal hostname even though nothing on your LAN can.

```yaml
action: opendisplay.drawcustom
target:
  device_id: <your display>
data:
  payload:
    - type: text
      value: "{{ state_attr('sensor.speiseplan_today', 'name') }}"
      x: 10
      y: 10
      size: 40
      color: red
    - type: dlimg
      url: "{{ state_attr('sensor.speiseplan_today', 'photo_url') }}"
      x: 200
      y: 50
      xsize: 200
      ysize: 200
```

**A meal without a photo still draws something.** `photo_url` answers with a QR code
linking to that recipe, so the display prompts you to fix it: scan, and SpeisePlan opens
on your phone at that recipe with the photo controls ready. It needs SpeisePlan's
`public_url` option set to an address your phone can reach — without it there is no
photo to serve and `photo_url` 404s. `has_photo` tells the two apart if you want to draw
something else instead.

**Guard the empty day.** With nothing planned at all, `photo_url` is `none` and the
template renders the string `"None"`, which fails the download. Put a condition on the
automation:

```yaml
condition:
  - condition: template
    value_template: "{{ state_attr('sensor.speiseplan_today', 'photo_url') != none }}"
```

Anything else that can reach SpeisePlan works the same way — the URL needs no
credentials:

```bash
curl -o today.png "$(...)/api/v1/recipes/7/photo"
```

SpeisePlan serves locally stored and externally hosted photos from that one endpoint, so
your renderer never has to care which kind a recipe has.

### Whole-week template

```jinja
{% for day in state_attr('sensor.speiseplan_meal_plan', 'days') %}
{{ day.weekday[:3] }} {{ day.date[-5:] }}  {{ day.meals | map(attribute='name') | join(', ') or '—' }}
{% endfor %}
```

## Installation

### HACS (custom repository)

This is distributed as a HACS **custom repository**, not through the default store.

In HACS: **⋮ → Custom repositories**, paste
`https://github.com/ajfriesen/ha-speiseplan-integration`, pick category **Integration**,
add it, then install SpeisePlan and restart Home Assistant. Updates come through HACS as
normal from then on.

### Manual

Copy `custom_components/speiseplan` into your Home Assistant `config/custom_components/`
directory and restart.

## Configuration

Open **Settings → Devices & services → Add integration → SpeisePlan** and enter:

| Field | Value |
| --- | --- |
| Host | Where SpeisePlan runs. As an add-on that is its internal hostname, like `49e94de4-speiseplan` — printed in the add-on log, and not the same as your Home Assistant host. |
| Port | `8080` by default |
| Uses HTTPS | Only if you put SpeisePlan behind a TLS reverse proxy |

SpeisePlan requires no credentials: its JSON API answers any request, which is why the
form asks only where it lives.

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
