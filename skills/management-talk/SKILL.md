---
name: management-talk
description: "Use when reporting to engineering leadership (directors, product managers, release managers) or shaping content for a channel (ticket comment, chat post, standup line, email, meeting points). Leads with impact, status, risk and ask."
---

# Management talk

Translate what engineers know into what decision-makers need. Keep it true; make it short.

## Know the reader and the channel first

- Reader: what do they decide or plan with this? (release date, priority, staffing, customer message)
- Channel: ticket comment, chat post, standup line, email or meeting points. Match its length and tone.

## Structure: impact, status, risk, ask

1. **Impact**: who or what is affected and how much, in business or user terms. Numbers when known.
2. **Status**: where things stand now (investigating, fix in review, fixed and verified, waiting on X) and the next date or milestone.
3. **Risk**: what could still go wrong or slip, how likely, and what it would cost. Say "unknown" when it is unknown.
4. **Ask**: what you need from them (a decision, approval, resource, nothing) and by when. If nothing is needed, say so.

Put the answer first. One idea per sentence.

## Rewrite rules

- Replace internals with effects: not "race in the cache invalidation path" but "some users saw stale prices for up to 5 minutes".
- Define a term once or drop it. No stack traces, function names or acronym piles.
- Keep every number and date that matters; never round a risk into reassurance.
- Do not hide bad news or soften a missed date. State the new date and what drives it.
- Do not claim more certainty than the evidence gives; mark unverified items.

## By channel

- **Standup line**: one sentence, status plus blocker.
- **Chat post**: three to five lines, impact first, a link for detail.
- **Ticket comment**: status, next step, and what is needed, in a few lines.
- **Email**: a plain subject that carries the status; the four parts as short paragraphs or bullets.
- **Meeting points**: three to five bullets the speaker can say aloud, ending with the ask.

Keep the original engineering detail available by link or in a `post-mortem`; do not paste it into the message.
