# Brag Plan: Charity Flow

## What is this app?
A donation and logistics platform: donors submit items, an admin reviews them and allocates them to a verified NGO, and the shipment is tracked until it is delivered. README: "An end-to-end donation and logistics management platform connecting generous donors with verified NGOs through an admin-moderated distribution pipeline."

## The angle
Most donation apps stop at "submit". Charity Flow's most impressive real thing is that the whole journey exists in one product, and every step is a status badge you can follow: `pending → accepted → allocated → at_hub → delivered`. The video follows ONE donation (a box of books) through that pipeline, calmly and confidently, using recreated UI from the real screens. The story is the pipeline, not a feature list.

## Hook (first ~4s)
Two lines of text on a clean light background: "A box of books." then "A verified NGO." (framing only, no product claim). The video then connects the two.

## Key moments (the middle)
- Donor form (from `donate.html`): drop-off location "Mumbai Central", category "Books", photo upload (JPG, PNG, WEBP — max 5 files, 5 MB each), description "excellent condition, all kinds of books available", "Submit Donation Request". Status badge lands as `pending`.
- Admin "Pending Inventory & NGO Allocation" card (from `item-allocation.html` screenshot): Books card, `Pending` badge, Accept button gets clicked, badge turns to `accepted`, then it is allocated to a verified NGO ("Helping Hands Trust", from `seed_ngos.py`).
- Logistics tracker: stages tick one by one `allocated → picked_up → at_hub → delivered`, matching README stages, with the audit log (ALLOCATION / UPDATE / DONATION tags as in the Reports screen) filling in alongside.

## Outro / punchline
"Charity Flow" with the app's own tagline "Overseeing Impact." and the live demo URL `charity-flow.onrender.com` (from README).

## User flow worth showing
1. Donor fills the donate form and submits (entry → key action).
2. Admin accepts it and allocates it to an NGO (key action).
3. Shipment progresses to `delivered`, with audit-log entries (result).

## Tone
- Preset: `polished`
- Creative direction: clean, confident product film; quiet premium, no jokes
- Interpretation: fewer scenes, long readable holds, soft crossfades, restrained SFX, no hype words.

## Format: landscape — 1920x1080
## Duration: ~30s (user-requested; overrides the skill's 15-25s default)

## Visual identity (from the project: `donate.html`, `admin.html` `:root`)
- Background: #f5f7fa (page `--bg-color`) / #f4f7f6 (admin `--light-bg`); cards white
- Primary / text: #1d3557 (navy)
- Accent: #e63946 (red, Logout button / active nav); secondary accent #457b9d (steel blue, submit button)
- Success green from Accept button: ~#2a9d8f (as seen in screenshot)
- Display + body font: Poppins (Google Fonts, 400/600 as the site loads); video will use Poppins 400/600/700
- Strongest visual element: white stat/inventory cards on pale grey with navy type, plus the status badges

## Privacy / grounding notes
- Screenshots contain account emails; the video will NOT show any emails. Recreated UI uses only: location, category, description, NGO name, stage names.
- Every claim is from README/code: stage names, upload limits, "Overseeing Impact.", live URL. No numbers invented (no "X donations", no speed claims).

## Share copy (draft)
Charity Flow follows one donation from a donor's form to a verified NGO — review, allocation, logistics and an audit trail in a single pipeline. Live demo below.

## Audio direction
- Role: warm bed with sparse professional accents
- Music: `happy-beats-business-moves-vol-10-by-ende-dot-app.mp3` (Sascha Ende, ende.app, CC BY 4.0), ~110 BPM, trimmed to ~30s, fade out over the last ~2.5s
- Music treatment: starts at 0 at low volume (~0.5), fade-in 0.8s; hold; fade out at the end
- Music cue guidance: bundled preset `cues/…vol-10…music-cues.json`. Strong cues: 15.82s (Accept click payoff), 20.19s (first logistics stage), 24.01s (outro title lands). Beat grid ≈0.55s apart.
- Audio-reactive treatment: subtle — music energy gently breathes the soft glow behind the title/outro card. No waveforms.
- SFX posture: sparse, motion-matched, low high-frequency-risk files (soft click on submit/Accept, soft switch on each stage tick, one soft impact on the outro title)
- Audio-coupled moments: typed description text; Accept click; four stage ticks; outro title
- Restraint rule: no stings on every element; nothing sharp or bright; music never competes with reading.

## Storyboard

### Scene 1 — Hook — 4.0s (0.0–4.0)
Pale #f5f7fa background, navy Poppins 600 text, centered. "A box of books." holds ~1.4s settled, then "A verified NGO." appears beneath it, holds ~1.6s. A thin red accent line draws between them.
Sequential/interaction: yes — two lines in sequence, each held ≥1.2s.
Audio intent: calm, confident opening; music fades in.
Audio-coupled idea: none
Transition mood: clean crossfade → Scene 2

### Scene 2 — Reveal — 4.2s (4.0–8.2)
"Charity Flow" large (Poppins 700, navy) with the README one-liner below it in two lines: "An end-to-end donation and logistics management platform" / "connecting donors with verified NGOs." (trimmed from README). Held ≥3s.
Sequential/interaction: none
Audio intent: title lands on beat (~4.10s)
Audio-coupled idea: soft impact on title
Transition mood: clean → Scene 3

### Scene 3 — Donor submits — 5.4s (8.2–13.6)
Recreated donate form card: "Select Drop-off Location: Mumbai Central", "Choose Item Category: Books", dashed upload box "Upload Photos (JPG, PNG, WEBP — Max 5 files, 5 MB each)" with "1 file(s) selected", description types out "excellent condition, all kinds of books available", cursor clicks "Submit Donation Request" (steel-blue #457b9d). A `pending` badge pops in.
Sequential/interaction: yes — fields fill in order, description types, cursor clicks submit.
Audio intent: tactile, light
Audio-coupled idea: subtle key ticks while typing; soft click on submit
Transition mood: slide/crossfade → Scene 4

### Scene 4 — Admin review and allocation — 5.5s (13.6–19.1)
Recreated "Pending Inventory & NGO Allocation" card: Books, `Pending` badge, Location: Mumbai Central, description. Cursor clicks green "Accept" (lands near strong cue 15.82s) → badge becomes `Accepted` and the allocation area opens with a "Select Target NGO" dropdown (Helping Hands Trust chosen); cursor clicks "Complete Allocation" and the badge reads "Allocated to Helping Hands Trust" (all from `item-allocation.html`). Caption: "Approve donations and assign them to active NGO requests in one step." (verbatim from the page).
Sequential/interaction: yes — click Accept, then allocation.
Audio intent: confident payoff at Accept
Audio-coupled idea: soft click on Accept; soft switch on allocation
Transition mood: clean → Scene 5

### Scene 5 — Logistics + audit trail — 4.9s (19.1–24.0)
Left: four-stage tracker `allocated → picked_up → at_hub → delivered` filling stage by stage (snapped to beats ≈ 20.19 / 20.74 / 21.83 / 22.92, so ~0.55–1.1s apart; stage names are short labels and the full row is then held ≥1.2s). Right: audit-log rows in the style of the Reports screen (tags ALLOCATION, UPDATE, DONATION) with fictional-neutral text e.g. "Donation allocated to Helping Hands Trust" / "Donation status updated to accepted" (no emails, no ids). Last stage turns green: `delivered`.
Sequential/interaction: yes — four stages tick in order.
Audio intent: momentum, then resolution
Audio-coupled idea: one soft switch per stage tick
Transition mood: clean → Scene 6

### Scene 6 — Outro — 6.0s (24.0–30.0)
"Charity Flow" (lands at strong cue 24.01s) + "Overseeing Impact." (the app's admin tagline) + "charity-flow.onrender.com". Held ≥4s, music fades out.
Sequential/interaction: none
Audio intent: warm resolve
Audio-coupled idea: one soft impact at title; subtle glow breathes with music
Transition mood: fade out

**Music mood for this video:** warm, upbeat-but-restrained corporate
**Audio summary:** Soft music bed fades in under the hook, tactile low-key UI sounds mark each real action, and the bed resolves into a calm fade under the outro.
