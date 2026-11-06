---
name: Lexora
description: The marked-up statute - a reviewed labour-law knowledge base worked directly on the text of the law.
colors:
  desk: "#e7e8e7"
  desk-deep: "#dfe1e0"
  paper: "#ffffff"
  ink: "#222426"
  ink-soft: "#3f4347"
  muted: "#595e63"
  rule: "#d6d8d8"
  rule-strong: "#b6babb"
  graphite: "#2a2d30"
  graphite-hover: "#15171a"
  focus-blue: "#2f5fc4"
  approve: "#1f7342"
  approve-soft: "#e3f2e8"
  reject: "#b3261e"
  reject-soft: "#fbe9e7"
  attention: "#8a5300"
  attention-soft: "#fff1d9"
  hl-actor: "#ffe36e"
  hl-action: "#b4ecbe"
  hl-object: "#cfe0ff"
  hl-party: "#ffc6da"
  hl-condition: "#ffd8a3"
  hl-measure: "#c2efe8"
  hl-other: "#e4e6e6"
typography:
  title:
    fontFamily: "'Source Serif 4 Variable', Georgia, serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  subtitle:
    fontFamily: "'Source Serif 4 Variable', Georgia, serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.3
  statute:
    fontFamily: "'Source Serif 4 Variable', Georgia, serif"
    fontSize: "17.5px"
    fontWeight: 400
    lineHeight: 1.9
  heading:
    fontFamily: "'Be Vietnam Pro', system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.35
  body:
    fontFamily: "'Be Vietnam Pro', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  label:
    fontFamily: "'Be Vietnam Pro', system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.55
  pencil:
    fontFamily: "'Source Serif 4 Variable', Georgia, serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sheet: "2px"
  control: "6px"
  panel: "8px"
  popover: "10px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.graphite-hover}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
    height: "38px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  button-quiet-hover:
    backgroundColor: "{colors.desk}"
  button-approved:
    backgroundColor: "{colors.approve-soft}"
    textColor: "{colors.approve}"
    rounded: "{rounded.control}"
  button-rejected:
    backgroundColor: "{colors.reject-soft}"
    textColor: "{colors.reject}"
    rounded: "{rounded.control}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 11px"
    height: "40px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-soft}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "1px 9px"
  chip-modality:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "1px 9px"
  panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.panel}"
    padding: "24px"
  sheet:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.sheet}"
  norm-flag:
    backgroundColor: "{colors.focus-blue}"
    textColor: "{colors.paper}"
    width: "40px"
    height: "26px"
  topbar:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-soft}"
    height: "56px"
  tooltip:
    backgroundColor: "{colors.graphite}"
    textColor: "{colors.paper}"
    rounded: "{rounded.popover}"
    padding: "14px 16px"
---

# Design System: Lexora

## Overview

**Creative North Star: "The Marked-Up Statute"**

The statute is the workspace.
Every extracted part of a norm is a highlighter stroke laid on its exact characters, the modality cue word is circled in pencil, and every norm is a numbered paper flag stuck to the right edge of the sheet.
The interface around the law is a quiet office: white printer paper resting on a pale graphite desk, graphite ink, graphite controls.

Colour belongs to the law, not to the software.
The highlighter pens carry meaning (who, does what, to what, for whom, under which condition, how much), so they are spent only where that meaning is being shown.
Everything else stays graphite and grey so that a reviewer on a projector or a reader at a desk sees the marked text first and the chrome last.

Density is a working desk, not a landing page: a sticky 56px top bar, an article index on the left, the sheet in the centre and a norm card on the right.
Serif speaks for the law and for page titles; sans speaks for the interface.

**Key Characteristics:**
- White paper sheets with a soft, low shadow on a pale grey desk ground.
- Six highlighter roles plus a neutral grey, always under ink-coloured text.
- Paper flags that overhang the sheet edge and change colour with the review decision.
- Pencil marginalia in italic serif, muted grey, rotated one degree.
- Graphite buttons, graphite tooltips, graphite toasts.
- Bilingual chrome (vi/en); statute text always Vietnamese.

## Colors

A near-neutral graphite office with one blue for focus and flags, three state colours for decisions, and a box of highlighter pens kept for the law.

### Primary
- **Graphite** (`graphite`): the only control colour. Primary buttons, the current step dot, the modality chip, avatars, the active nav underline, tooltips and toasts.
- **Pressed Graphite** (`graphite-hover`): hover state of the primary button.

### Secondary
- **Ballpoint Blue** (`focus-blue`): focus rings, input focus borders, links, citation numbers in chat, and the pending paper flag. Text selection uses it at 24% alpha.

### Tertiary (decision states)
- **Approved Green** (`approve`, soft `approve-soft`): a norm or step already approved. Approved flags, the pressed Approve button, completed step dots, the public chip.
- **Rejected Red** (`reject`, soft `reject-soft`): a norm already rejected, error toasts, the strike-through on rejected highlights.
- **Attention Ochre** (`attention`, soft `attention-soft`): coverage gaps (a sentence with a normative cue and no norm), warning reasons on a norm card, private-KB chip, warn notices.

### Highlighter roles
Text on every highlighter stays `ink`; all pass 7:1.
At rest a stroke is the pen colour mixed to 62% over the paper; hover and focus show it at full strength.
- **Actor Yellow** (`hl-actor`): the subject who bears the norm.
- **Action Green** (`hl-action`): the act.
- **Object Blue** (`hl-object`): what the act is about.
- **Party Pink** (`hl-party`): recipient, beneficiary and counterparty share one pen.
- **Condition Orange** (`hl-condition`): conditions and exceptions share one pen.
- **Measure Mint** (`hl-measure`): quantities and deadlines share one pen.
- **Plain Grey** (`hl-other`): an outcome, or a norm the rules could not structure (the whole quote is marked grey).

### Neutral
- **Desk** (`desk`): the page ground, quiet-button and nav hover fill, segmented control track.
- **Deep Desk** (`desk-deep`): a second ground tone for recessed areas.
- **Paper** (`paper`): sheets, panels, cards, inputs, top bar.
- **Ink** (`ink`): body and statute text.
- **Soft Ink** (`ink-soft`): secondary text, nav links, slot labels, hover borders, the pencil ring around the modality cue.
- **Pencil Grey** (`muted`): hints, labels, marginalia, provenance lines.
- **Rule** (`rule`) and **Strong Rule** (`rule-strong`): hairline dividers and table rules; control and chip borders.

### Named Rules
**The Pens Belong To The Law Rule.** Highlighter colours appear only on statute text, the colour legend, role swatches and illustrative statute quotes. Never on chrome, navigation, avatars, buttons or citations.

**The Graphite Controls Rule.** Every control is graphite or paper. Green and red mark only a decision already taken (a pressed Approve or Reject, a decided flag), never an invitation to act.

**The Ink On Every Pen Rule.** Highlighted text keeps `ink`; colour is never the only signal, so every role also carries its name in the card, legend and glossary tip.

## Typography

**Display Font:** Source Serif 4 Variable (optical size axis, with italic; fallback Georgia, serif)
**Body Font:** Be Vietnam Pro 400/500/600 (fallback system-ui, sans-serif)

Both are self-hosted through @fontsource; the app makes no font requests at runtime.

**Character:** a bookish serif that reads like printed legislation, paired with a Vietnamese-first sans whose diacritics stay crisp at small interface sizes.

### Hierarchy
- **Title** (serif 600, 28px, 1.2, -0.01em; 24px under 760px): page titles.
- **Subtitle** (serif 600, 20px, 1.3): section titles inside a page.
- **Statute** (serif 400, 17.5px, 1.9, pre-wrap; article lines 600): the law on the sheet. The generous leading leaves room for highlighter strokes and the pencil ring.
- **Heading** (sans 600, 16px, 1.35): panel and card headings, the norm card title.
- **Body** (sans 400, 15px, 1.55, tabular numerals): interface text. Lead paragraphs cap at 68ch.
- **Label** (sans 500, 13px, muted): field labels, table headers, legend captions.
- **Pencil** (serif italic, 14px, 1.5, muted; 13.5px in the margin): marginalia, reviewer and AI notes.

### Named Rules
**The Two Voices Rule.** Serif is the voice of the law and of page titles; sans is the voice of the software. A control never sets in serif, and statute text never sets in sans.

**The No Eyebrow Rule.** Headings stand alone. No small label, kicker or uppercase tag sits above a title or heading.

## Layout

Pages sit in a centred frame of max 1320px with 32px side padding and 96px bottom padding (20px / 16px / 80px under 760px).
A page head puts the title and lead on the left and its actions bottom-aligned on the right, wrapping when narrow.
Spacing steps are 4, 8, 16, 24 and 32px; 28px separates major columns.

The review screen is three columns: article index with per-article progress and the colour legend, the statute sheet, and the norm card.
A sticky footer bar carries the remaining-work summary and the next step.
Chat is a 300px sticky setup column beside a conversation capped at 900px, with the question box sticky at the bottom.
Under 900px columns stack; under 760px phones get lookup and reading only, and the authoring and admin nav groups are hidden.

**The Margin Earns Its Column Rule.** A statute unit gets a 150px margin-note column only when it carries a note; otherwise the text runs the full sheet width.

## Elevation & Depth

Hybrid: paper lifts off the desk with a soft shadow, while panels and controls are flat with hairline borders.

### Shadow Vocabulary
- **Sheet** (`0 1px 2px rgb(20 22 24 / 0.08), 0 8px 24px rgb(20 22 24 / 0.07)`): the statute sheet and the norm card, the things that are "paper".
- **Pop** (`0 2px 6px rgb(20 22 24 / 0.12), 0 14px 36px rgb(20 22 24 / 0.16)`): floating layers only: user menu, glossary tooltip, toast, the sticky chat question box.
- **Flag** (`0 1px 2px rgb(20 22 24 / 0.2), 0 3px 8px rgb(20 22 24 / 0.12)`): paper flags stuck on the sheet edge.

### Named Rules
**The Paper Lifts, Chrome Lies Flat Rule.** Only paper objects and floating layers cast shadows; panels, chips, inputs and the top bar use 1px rules instead.

## Shapes

Corners are nearly square on paper (2px), gently rounded on controls (6px) and panels (8px), softer on floating dark layers (10px), and fully round on chips, segmented controls, avatars and the modality cue ring.
Paper flags are square on the side stuck to the sheet and rounded 4px on the free side, like a sticky tab.
Borders are 1px hairlines; the inline editor and similar sub-areas open below a 1px dashed rule.
There are no coloured side stripes on cards, notices or quotes.

## Components

### Buttons
Plain, graphite and confident; they never borrow a pen.
- **Shape:** gently rounded (6px), min height 38px (32px small), 16px inline SVG icon with an 8px gap.
- **Primary:** solid graphite with white text; hover deepens to pressed graphite. One primary per region.
- **Secondary:** paper with a strong-rule border; hover darkens the border to soft ink.
- **Quiet:** transparent, soft-ink text; hover fills with desk.
- **Decided:** a pressed Approve becomes soft green with green text and weight 600; a pressed Reject becomes soft red with red text. Before a decision, Approve is primary graphite and Reject is quiet.
- **Press / Disabled:** 1px downward nudge on press; 50% opacity when disabled.
- **Focus:** 2px ballpoint-blue outline, 2px offset.

### Chips
- **Style:** pill (999px), 12.5px sans 500, strong-rule border, paper fill, soft-ink text.
- **Modality chip:** solid graphite with white text, the norm card's type of norm.
- **Status chips:** outline only, tinted by state (public green, private ochre, synthetic red).

### Cards / Containers
- **Sheet:** paper, 2px corners, sheet shadow, no border. Holds the statute and the norm card.
- **Panel:** paper, 8px corners, 1px rule border, 24px padding, flat.
- **Notice:** 8px corners with a tinted fill and matching border (info blue, warn ochre, error red); never a side stripe.
- **Choice card:** a radio rendered as a bordered panel; checked gets a graphite double border.

### Inputs / Fields
- **Style:** paper fill, 1px strong-rule border, 6px corners, min height 40px, label 14px 500 above, hint 13px muted below.
- **Focus:** border turns ballpoint blue with a 3px blue halo at 18% alpha.

### Navigation
- **Top bar:** sticky, 56px, paper with a bottom rule. Brand (serif 19px), zone groups separated by a vertical rule, then About, language toggle and user menu on the right.
- **Links:** 500 soft ink, 36px tall, 6px corners; hover and current fill with desk; current also gets a 2px graphite underline at the bar's bottom edge.
- **Steps:** numbered dots; current is graphite, completed is green, upcoming is an outlined paper dot.
- **Segmented filter:** desk track, pill buttons, the pressed one becomes a paper pill with a hairline shadow.

### Statute Sheet (signature)
- **Highlights:** each slot is a stroke on its exact character range at 62% of its pen, with 2px corners and clone decoration across line breaks; hover and focus show the full pen. The focused norm also gets a 2px dark underline and a left-to-right swipe animation (0.42s).
- **Modality cue:** a 1.5px soft-ink pencil ring, fully round, around the cue word.
- **Rejected:** the stroke disappears and the text is struck through in red and muted.
- **Coverage gap:** a 2px dotted ochre underline; resolved gaps turn rule-grey.
- **Paper flags:** 40 x 26px numbered tabs overhanging the sheet's right edge by 14px. Blue pending, green approved, red rejected, ochre "?" for a gap, grey for a resolved gap. Hover slides out 3px, the selected flag slides 6px and gets a paper plus soft-ink double ring. Flags are the keyboard path to every norm.
- **Marginalia:** italic serif pencil notes, muted, rotated -1deg, in the margin column.

### Norm Card
A paper sheet that mirrors the selected flag: the same numbered tab, the norm sentence as heading, chips for modality and origin, a definition list of slots where each label carries its role swatch, attention reasons in ochre with a warning icon, pencil notes, and the Approve / Reject / Edit row.

### Glossary Tip
Dotted-underline terms (`help` cursor) open a graphite card (10px corners, pop shadow) with a serif term name, definition, cue words and an illustrative example in which the illustrated part is marked with Actor Yellow.

### Citations
A cited passage is a slip with the quote in 17px text; the cited span is marked in graphite pencil: a 6% graphite wash with a 1.5px soft-ink underline. Citation numbers are ballpoint blue.

### Toast
Graphite (red for errors) bottom-centre bar with soft corners (10px), pop shadow, rises 8px on entry. Messages are translated at render time, so switching language re-renders them, and they clear on navigation.

## Do's and Don'ts

### Do:
- **Do** keep every control graphite or paper; primary is solid graphite.
- **Do** use green and red only to show a decision already taken.
- **Do** keep highlighted text in `ink` and name every role in words alongside its colour.
- **Do** mark citations with the graphite pencil underline, never with a highlighter pen.
- **Do** give a statute unit a margin column only when it carries a note.
- **Do** let paper (sheet, norm card) cast the sheet shadow and keep panels flat with 1px rules.
- **Do** translate toasts at render time and clear them on navigation.
- **Do** set the law in Source Serif 4 at 17.5px / 1.9 and the interface in Be Vietnam Pro.

### Don't:
- **Don't** put highlighter colours on chrome, nav, avatars, buttons or citations.
- **Don't** place eyebrows, kickers or uppercase labels above headings.
- **Don't** use coloured side stripes on cards, notices or quotes.
- **Don't** colour an Approve or Reject button green or red before the reviewer has decided.
- **Don't** add a seventh highlighter; new slot types share an existing pen (as party, condition and measure already do).
- **Don't** cast shadows from panels, chips, inputs or the top bar.
