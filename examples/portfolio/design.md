# design.md — Alex Taylor Portfolio

> Design system for the portfolio **slide deck** (`deck.html`) and **online view** (`index.html`).
> Governing skill: `.agents/skills/minimalist-ui` (Leonxlnx/taste-skill-classics, *Premium Utilitarian Minimalism*).
> Content source of truth: `config/profile.example.md` and `../cv.example.md`. Nothing on any slide or page may claim more than those files.

---

## 1. Intent

A calm, document-style portfolio that reads like a well-kept workspace. It should make the case that
Alex is **organized, accurate and discreet**, so the design itself has to be organized, accurate and quiet.

- **Audience:** remote hiring managers and agency owners (OnlineJobs.ph, LinkedIn), scanning in under 60 seconds.
- **Primary message:** "Remote admin, recruitment and data support you can hand things to."
- **Tone:** plain, specific and first-person. No hype.

## 2. Brand tokens

### Color: warm monochrome with spot pastels

| Token | Hex | Use |
|---|---|---|
| `--canvas` | `#FBFBFA` | Page / slide background |
| `--bone` | `#F7F6F3` | Alternating section bands, `<kbd>`, inline chips |
| `--surface` | `#FFFFFF` | Cards |
| `--ink` | `#111111` | Headings, primary buttons |
| `--text` | `#2F3437` | Body copy |
| `--muted` | `#787774` | Secondary text, labels, meta |
| `--line` | `#EAEAEA` | Every border and divider (1px solid, always) |
| `--red-bg` / `--red` | `#FDEBEC` / `#9F2F2D` | Tag: Confidential / NDA |
| `--blue-bg` / `--blue` | `#E1F3FE` / `#1F6C9F` | Tag: Recruitment |
| `--green-bg` / `--green` | `#EDF3EC` / `#346538` | Tag: Data & Records |
| `--yellow-bg` / `--yellow` | `#FBF3DB` / `#956400` | Tag: Content & Media |

The four pastels are a **fixed category system**, so the same color always means the same work type in both the deck and the web view.
Never use pure `#000`, gradients, neon colors, or colored hero blocks.

### Typography

| Role | Family | Settings |
|---|---|---|
| Display / headings | **Instrument Serif** | `letter-spacing: -0.03em; line-height: 1.05` |
| Body / UI | **Geist** | `line-height: 1.6`, weights 400 / 500 / 600 |
| Meta / labels / numbers | **Geist Mono** | Uppercase labels at `0.72rem` with `letter-spacing: 0.08em` |

Banned: Inter, Roboto, Open Sans.

Scale (web): `h1 clamp(3rem, 7vw, 5.5rem)` · `h2 clamp(2.2rem, 4vw, 3.25rem)` · `h3 1.25rem` · body `1.0625rem`.
Scale (deck, 1920×1080): title `140px` · slide heading `88px` · body `30px` minimum · labels `20px` mono.
Audience-readable text is **never below 28px** on a slide.

### Shape, depth and spacing

- Radius: cards `12px`, buttons `6px`, `<kbd>` `4px`. Pills are only for small tags.
- Shadows: none at rest. On hover, use only `0 2px 8px rgba(0,0,0,0.04)`.
- Spacing scale: 4 · 8 · 12 · 16 · 24 · 40 · 64 · 96 · 128 px.
- Web sections: `padding-block: 128px` on desktop, `80px` on mobile. Content max-width is `1040px`, and reading text is `680px`.
- Deck safe area: `120px` horizontal and `96px` vertical padding on a 1920×1080 canvas.

### Iconography

Inline SVG primitives in a Phosphor-Bold-like style (2px stroke, square caps), drawn in `--ink` on a pastel tile.
No Lucide, Feather or Heroicons, and no emoji anywhere.

### Texture

To avoid flat emptiness, the hero and title slide get one warm radial light spot (`rgba(214,196,160,0.10)`) plus a faint 1px dot grid at `opacity: 0.35`.
Nothing else gets decoration.

## 3. Motion

- Scroll entry: `opacity 0 → 1`, `translateY(12px → 0)`, `600ms cubic-bezier(0.16,1,0.3,1)`, triggered by `IntersectionObserver`.
- Stagger: `calc(var(--i) * 80ms)`.
- Deck transitions: 400ms opacity crossfade between slides, with the same easing. Slides never slide or zoom.
- All of this sits behind `prefers-reduced-motion: no-preference`. The reduced-motion setting shows everything immediately.
- Only `transform` and `opacity` are animated.

## 4. Components

| Component | Spec |
|---|---|
| **Bento card** | `--surface`, `1px solid var(--line)`, radius 12, padding 32–40, asymmetric grid (e.g. 7/5, 5/7, 4/4/4 columns) |
| **Tag** | Pill, `0.7rem` mono uppercase, `letter-spacing .06em`, pastel bg plus matching text color |
| **Metric** | Serif numeral (large) above a mono label. Use only verified numbers: **~30** postings/day, **30** recruits, **200+** member records, **4** certifications |
| **Primary button** | `--ink` bg, white text, radius 6, `:hover #333`, `:active scale(.98)` |
| **Ghost button** | Transparent, `1px solid var(--line)`, ink text |
| **Timeline row** | No boxes: mono date column, serif role, muted org, with a `border-bottom` divider |
| **Window chrome** | White top bar with three `#E5E5E3` dots, used to frame workflow mock-ups (pipeline tracker) |
| **kbd** | Used for deck controls: `←` `→` `F` `P` |

## 5. Information architecture

Both views share one narrative, in this order:

1. **Title:** name, role line, location, availability
2. **About:** 3-sentence summary
3. **By the numbers:** four verified metrics
4. **Case 01: Recruitment pipeline ops** (Financial Services Agency agency manager, freelance)
5. **Case 02: Confidential data encoding** (independent CPA, freelance)
6. **Case 03: 200+ member records system** (Student Tech Society Membership & Election)
7. **Case 04: Content & media production** (Canva / CapCut, Student Tech Society Media)
8. **Case 05: CampusCart capstone:** system analysis and documentation
9. **Toolkit:** grouped tools
10. **Certifications:** 4 Certiport credentials
11. **Experience timeline**
12. **Contact:** email, LinkedIn, live resume

Each case uses the same frame: **Context → What I did → Tools → Outcome**.

> [!IMPORTANT]
> **NDA rule.** Client deliverables are confidential. Case studies describe *process and outcome* only. They contain no client names beyond what the resume already states, no screenshots of real data, and no invented metrics. Mock-ups are visibly labeled "Illustrative sample, not client data."

## 6. Deck specifics (`deck.html`)

- Fixed 1920×1080 stage, scaled to fit the viewport (letterboxed on `--bone`).
- Controls: `→` / `Space` / click for next, `←` for previous, `Home`/`End`, `F` for fullscreen. The URL hash `#3` deep-links to a slide.
- Mono footer on every slide: `ALEX TAYLOR · PORTFOLIO 2026` on the left and `03 / 12` on the right.
- **PDF export:** browser Print, then Save as PDF. Print CSS sets `@page { size: 1920px 1080px; margin: 0 }`, so each slide becomes one page.

## 7. Online view specifics (`index.html`)

- Single scrolling page with a sticky, blurred top bar showing the name and section anchors.
- Responsive: bento grids collapse to one column below `760px`.
- Semantic landmarks (`header`, `main`, `section[aria-labelledby]`, `footer`), visible focus rings (`2px solid #111`, offset 3px), and AA contrast throughout.
- A "View as slides" ghost button links to `deck.html`.

## 8. Copy rules

- Banned words: *elevate, seamless, unleash, next-gen, game-changer, delve, passionate, synergy*.
- Lead with verbs and numbers: "Publish ~30 job posts a day" rather than "Responsible for job posting."
- No placeholder names or lorem ipsum.

## 9. Open items

- [ ] Professional headshot. Until one exists, an initials monogram `AT` stands in.
- [ ] Personal, unbranded Canva / CapCut samples to replace the Case 04 placeholder tiles.
- [ ] Hosting decision for the online view (Netlify, Vercel or GitHub Pages).
