---
version: 1
slug: "frontend-src-routes"
primary_target: "frontend/src/routes"
related_targets: []
---

# Lexora workspace (SvelteKit app)

Scope: every app screen of the new SvelteKit frontend (login, overview, knowledge bases, import, review, preview and publish, chat, users admin, about). Visitor mode: Operate. Desktop first; phones need lookup and reading only.

Audience and job: corporate legal reviewers import statutes, check each extracted norm against the exact text and publish; HR readers ask questions over published knowledge bases and open the cited sentence. Admins manage accounts. Roles: admin, reviewer, reader.

Constraints: local loopback, FastAPI serves the static build, no network at runtime (fonts self-hosted), bilingual vi/en with statute text always Vietnamese, WCAG 2.2 AA, colour never the only signal.

## Direction contract

THESIS: The statute is the workspace. Every extracted part is a highlighter stroke on the exact words and every norm is a paper flag in the margin; refuses the category default of a chat window beside a document preview.

OWN-WORLD: White printer paper on a pale graphite desk ground, graphite ink, five highlighter roles (yellow actor, green action, blue object, pink recipient or beneficiary, orange condition), blue and green paper flags, pencil-grey marginalia in italic serif. Standard web controls in graphite; highlighter colour only on statute text, legends and role chips.

STORY: Reviewers see what the machine proposed on the law itself, approve or fix it span by span, and publish a versioned base. Readers ask, get cited sentences, and trust them because each citation opens the highlighted source.

FIRST VIEWPORT: Review screen at 1440x900: 56px top bar (brand, zone tabs, user), left article index with per-article progress and the role key, the statute sheet centred with highlights and margin flags, right norm card with role-keyed slots and Approve, Reject, Edit.

FORM: Marked-up statute copy, position 1 on the ordered list (picked over the assigned pocket law code). seed:251a2edc3970938b

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
