# STEP-12 — Deliver: email-shaped output

## What I did

- Implemented `deliver` — the final node. Reads the draft and
  synthesis; emits a `FinalBrief` with `subject`, `html_body`,
  `plain_text_body`. Three strings. Same pattern as everything else.
- Wrote the deliver prompt to render the brief as email-ready
  content: editorial subject (not generic templated), simple
  email-safe HTML, parallel plain-text version.
- Migrated `research_news` from `create_agent` to `bind_tools +
  with_structured_output` after a test run finally reproduced the
  flakiness predicted in STEP-05.
- Closed Phase 1: full pipeline runs end-to-end, produces email-shaped
  output, 35 tests green.

## What I learned

### Naming the deployment context shaped the design

"Where does this output go?" was the first question. Answer: a Lambda
calls the agent, takes the output, hands it to SES or Mailgun.

That made the design concrete. Deliver doesn't *send* anything; it
produces three fields that an email service needs and lets the
deployment harness handle the transport. This separation is correct:
the agent owns content, the harness owns delivery.

Without naming the deployment context, deliver would have been some
generic "format the output" node and the design would have been
blurry. With it, the schema is exactly the three fields SES needs.

### Subjects should be editorial, not templated

The default for daily briefs is something like "WTI Daily Briefing —
2026-05-07". This is wasted real estate. The inbox preview is the one
place to communicate today's actual story.

The deliver prompt asks for a 50-70 character subject that captures
the dominant narrative, with explicit bad/good examples:

- *Bad:* "Daily Crude Oil Briefing — May 7, 2026"
- *Good:* "Crude pauses on demand fears; Hormuz premium intact"

Output reflects this. Subjects are concrete, story-driven, specific to
the day's actual analysis.

The cost is one extra LLM call's worth of effort. The benefit is the
inbox preview earns its keep. Worth it.

### Email HTML is its own world

The HTML guidance in the prompt is heavily defensive:

- `<h1>`, `<h2>`, `<p>` only
- Inline `style` attributes if any styling is needed
- No `<style>` blocks, no external CSS
- No `<table>` layouts
- No images, no JS

Outlook in particular ignores or mangles modern CSS, external
references, and most layout primitives. Plain semantic HTML with
inline styles is what survives across clients.

The prompt explicitly tells the model: "Outlook will mangle anything
fancy. Keep it boring and reliable."

This is one of those cases where naming the constraint concretely in
the prompt produces better output than abstract "compatibility
matters" framing.

### Plain text is a fallback, not a duplicate

Some email clients prefer plain text. Some users do. SES recommends
sending both bodies; the client picks.

Plain text isn't the HTML with tags stripped. It's its own format,
with text-only structure (headings as `=====` underlines, paragraph
breaks via blank lines). The prompt produces it as a parallel render
of the brief, not a transformation of the HTML.

### "Don't rewrite the prose"

The most consequential instruction in the deliver prompt:

> Render the brief sections as written. Don't edit, condense, or
> rewrite the prose. Your job is structural rendering, not editing.

Without this, the model "helpfully" improves the brief while
rendering — undoing the work of draft and sense-check. The
instruction is repeated twice in the prompt. Even so, occasional
drift happens; sense-check would catch it if it weren't already past
that node.

The deliver step deliberately doesn't have an auditor. The brief has
already been audited; deliver is just rendering. If deliver edits the
prose, it's bypassing the audit. Hence the strong instruction.

### News migration finally happened

The `create_agent` flakiness in news (predicted in STEP-05) finally
manifested during deliver's testing. Test run produced
`ValueError: Native structured output expected valid JSON for
NewsResearch, but parsing failed: Extra data: line 1 column 1929`.

Same failure as catalysts back in STEP-06. The fix took ~10 lines:
swap `create_agent` for `bind_tools + with_structured_output`, same
as catalysts and geo.

The lesson I should have acted on earlier: when the same failure
mode is predicted and one instance has already manifested, migrate
the others *before* they fail in production. I didn't. The migration
was deferred until news broke. It's a small mistake but a real one;
the fix could have happened during the catalysts PR and saved the
debugging time later.

### Phase 1 closed

After deliver merged, the pipeline runs end-to-end and produces a
deliverable. The remaining work for Phase 1 was non-feature:
formatting/linter setup, tutorial documentation (these files), and
the retrospective.

Closing principle: when the feature work is genuinely done, name it
done. Don't pretend tutorial gaps or formatting debt blocks
"completion" — those are post-feature work, and naming them as such
is honest sequencing.

## What surprised me

- That `with_structured_output` works as well for HTML+text rendering
  as for everything else. I expected to need free-form output and
  post-processing.

- How much the deployment context (Lambda → SES) clarified the
  design. Vague specs produce vague code; concrete deployment
  contexts produce concrete code.

- That subjects are dramatically better when given concrete bad/good
  examples in the prompt. The model defaults to template-shaped
  subjects without them.

## Open questions

- Should deliver also produce a JSON body for clients that prefer
  structured input (e.g., Slack, Teams)? Trivially yes if needed —
  add a fourth field. For Phase 1, email is the only target.

- Should the subject include a date prefix (`[2026-05-07] ...`) for
  inbox sorting? Currently no — the prompt explicitly avoids it.
  Could be a per-deployment toggle.

## Glossary

- **Deployment harness** — The thing that runs the agent and
  transports its output. For this project, the planned harness is a
  Lambda + SES setup. The agent doesn't know or care about the
  harness; it produces content, the harness handles delivery.
- **Final node** — The graph's last node. Writes whatever the
  caller will consume. In agent-shaped graphs, this is often the
  point where structure shifts from "internal state" to "output
  format."
