# Deliver — render the brief as email-ready content

The brief has been drafted and audited. Your job is to produce the
final output that a Lambda will hand to an email service (SES or
Mailgun) for sending.

## Today's context

- **Date:** {target_date}
- **Commodity:** {commodity}

## Synthesis (for subject line)

{synthesis}

## The brief

### Price section
{price_section}

### News section
{news_section}

### Catalysts section
{catalysts_section}

### Geopolitics section
{geopolitics_section}

## What you're producing

Three fields:

### subject

A single-line email subject, 50–70 characters, that captures the
day's dominant story. The reader sees this in their inbox preview.
Make it specific, not generic.

Bad: "Daily Crude Oil Briefing — May 7, 2026"
Good: "Crude pauses on demand fears; Hormuz premium intact"

Lead with the story, not the date or commodity name. The reader
already knows what they're subscribed to.

### html_body

The brief rendered as simple, email-compatible HTML. Use:

- `<h1>` for the briefing title (commodity + date)
- `<h2>` for each section heading (Price, News, Catalysts, Geopolitics)
- `<p>` for paragraphs within sections
- Inline `style` attributes if any styling is needed; no `<style>`
  blocks, no external CSS
- No `<table>` layouts, no `<div>` nesting beyond what's needed
- No images, no links to external CSS, no JavaScript

Keep it boring and reliable. Outlook will mangle anything fancy.

The structure should be:
