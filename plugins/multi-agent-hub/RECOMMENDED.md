# Claude-only plugins (listed, not installed by this marketplace)

Install each from its own upstream marketplace in a Claude Code session. Marketplace names were read from each
upstream `.claude-plugin/marketplace.json`; if a command fails, check `/plugin`. Review a plugin and its licence before
installing it; nothing here is installed automatically.

| Plugin | What it gives | Claude install |
|---|---|---|
| engineering | Engineering workflows: standups, code review, architecture decisions, incident response | `/plugin marketplace add anthropics/knowledge-work-plugins` then `/plugin install engineering@knowledge-work-plugins` |
| design | Design workflows: critique, design systems, UX writing, accessibility audits, research | same marketplace, `/plugin install design@knowledge-work-plugins` |
| claude-security | Deep vulnerability scanning of your own code inside the session | `/plugin marketplace add anthropics/claude-plugins-official` then `/plugin install claude-security@claude-plugins-official` |
| anthropic-skills (`document-skills`, `example-skills`, skill-creator, ...) | docx, pdf, pptx, xlsx and example skills; licensing is per skill (see https://github.com/anthropics/skills/blob/main/README.md and each skill's own LICENSE file) | `/plugin marketplace add anthropics/skills` then `/plugin install document-skills@anthropic-agent-skills` (also `example-skills@anthropic-agent-skills`) |
| agent-engineering | Playbook for coding agents: plan, implement with checks, review independently, publish (otaviobarros/agent-engineering) | `/plugin marketplace add otaviobarros/agent-engineering` then `/plugin install agent-engineering@agent-engineering` |
| mattpocock-skills | Matt Pocock's engineering skills (mattpocock/skills) | `/plugin marketplace add mattpocock/skills` then `/plugin install mattpocock-skills@mattpocock` |
| design-skills | Ten UX and design framework skills (cuellarfr/design-skills) | `/plugin marketplace add cuellarfr/design-skills` then `/plugin install design-skills@design-skills` |
| vectorlab-ux-skills | UI/UX, microcopy and visual taste skills (VectorLabAU/skills) | `/plugin marketplace add VectorLabAU/skills` then `/plugin install vectorlab-ux-skills@vectorlab` |
| agent-estimate | PERT three-point estimation, METR thresholds, wave planning (kiloloop/agent-estimate) | `/plugin marketplace add kiloloop/agent-estimate` then `/plugin install agent-estimate@agent-estimate-marketplace` |
| caveman | Terse reply style (akramsystems/caveman) | `/plugin marketplace add akramsystems/caveman` then `/plugin install caveman@akramsystems-plugins` |

Their skills are `SKILL.md` directories that may be copied into `~/.codex/skills` by hand for Codex use only if the whole
skill directory is copied (scripts, references, licence files), its licence allows it, its dependencies and external
programs are installed, and it is checked to run on Codex; some skills (for example docx) need bundled scripts and
external tools and may not work there.
