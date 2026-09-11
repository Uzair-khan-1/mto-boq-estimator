# AI Residential MTO/BOQ Estimator (MVP)

An AI-assisted, engineer-controlled tool that turns one or more simple
residential RCC drawings (PDF/PNG/JPG - e.g. separate Plan, Elevation, and
Section files) plus a few project inputs into a **preliminary** Material
Take-Off (MTO), Bill of Quantities (BOQ), and cost estimate — exportable to
Excel and PDF.

> ⚠️ **Disclaimer**: This tool produces **preliminary, indicative**
> quantities and costs for early-stage budgeting only. It is **not** a
> substitute for a licensed structural engineer's design, a detailed BOQ
> prepared from approved drawings, or a certified quantity surveyor's
> estimate. Always get professional verification before using these
> numbers for tendering, construction, or financial decisions.

---

## 1. Why this architecture

The single most important design decision in this project:

**The LLM (Groq) never calculates final quantities.**

Vision-language models are good at *reading* a drawing — spotting a grid of
columns, guessing a slab thickness note, reading a dimension string — but
they are unreliable at *arithmetic* and have no memory of engineering
formulas. So this app splits the pipeline in two:

1. **AI interpretation layer** (`ai/`) — Groq's vision-capable LLM looks at
   the drawing image(s) plus any OCR'd text and returns a **structured JSON**
   guess of building parameters (floors, footing type, column count/size,
   beam count/size, slab area/thickness, wall length, openings, etc.),
   each with a **confidence level** (High/Medium/Low) and a short reason.
2. **Deterministic engineering layer** (`engineering/`) — plain Python
   functions implement standard civil-engineering thumb-rule formulas
   (excavation volume, concrete volume, steel-by-thumb-rule, formwork
   contact area, masonry/plaster area, etc.). These functions are pure,
   unit-tested-friendly, and 100% traceable — every number in the final
   BOQ can be traced back to an input parameter and a named formula.

Between steps 1 and 2 sits a **mandatory human-in-the-loop review screen**:
the user sees every AI-extracted parameter, its confidence level, and can
edit any value before a single quantity is calculated. Nothing the LLM says
is trusted blindly.

```
Upload drawing + project inputs
        │
        ▼
PDF/Image processing (PyMuPDF, OpenCV, EasyOCR)
        │
        ▼
Groq Vision LLM  →  structured JSON (ExtractedBuildingParams)
        │                                   with confidence per field
        ▼
User verification / edit screen  (Streamlit)
        │
        ▼
Deterministic engineering calculations (engineering/calculations.py)
        │
        ▼
MTO  →  BOQ (rates + wastage)  →  Cost Estimate
        │
        ▼
Excel (openpyxl) + PDF (ReportLab) export
```

---

## 2. What's included in the MVP

Supports simple **1–2 storey RCC residential buildings** (isolated footings,
rectangular columns, rectangular beams, flat RCC slabs, brick/block infill
walls) and estimates:

- Earthwork excavation (footings/trenches, incl. working-space allowance)
- Anti-termite treatment & PCC (lean concrete) below footings
- Footing concrete + reinforcement
- Column concrete + reinforcement (main bars + stirrups thumb-rule)
- Beam concrete + reinforcement
- Slab concrete + reinforcement
- Formwork/shuttering contact area (footings, columns, beams, slabs)
- Masonry / blockwork (openings deducted)
- Plaster (internal + external, openings deducted)
- Flooring (built-up area allowance)
- Roof waterproofing
- Painting (internal + external, tied to plaster area)
- DPC (damp-proof course) at plinth level
- Preliminary reinforcement **allowance** as a % check against thumb-rule
  steel (sanity cross-check, flagged if they diverge a lot)
- A generic "Preliminaries & Contingency" BOQ line (%-based, editable)

Every quantity row carries: **formula name, inputs used, confidence,
assumption notes**, visible in an expandable "Calculation Breakdown" panel.

### Explicitly out of scope for this MVP (documented, not silently dropped)
- Detailed structural design / bar bending schedules
- MEP (electrical, plumbing, HVAC) quantities — only a lump-sum
  "Preliminaries" placeholder line is included
- Non-RCC structural systems (steel frame, load-bearing masonry without RCC
  frame, sloped/truss roofs)
- Multi-wing / irregular floor plans beyond basic rectangle decomposition
- Seismic/wind design checks

---

## 3. Project structure

```
mto_boq_estimator/
├── app.py                      # Streamlit entrypoint / page router
├── config.py                   # App-wide constants & settings
├── requirements.txt
├── .streamlit/
│   └── config.toml             # Theme + upload size
├── models/
│   └── schemas.py              # Pydantic models (single source of truth)
├── ai/
│   ├── groq_client.py          # Groq API wrapper (vision + text)
│   ├── prompts.py              # System/user prompt templates
│   └── extraction.py           # Orchestrates AI extraction -> Pydantic
├── drawing_processing/
│   ├── pdf_processor.py        # PyMuPDF: PDF -> images, text layer
│   ├── image_processor.py      # OpenCV: cleanup, deskew, resize
│   └── ocr_engine.py           # EasyOCR wrapper, dimension-text helpers
├── engineering/
│   ├── rules.py                # Thumb-rule constants & default assumptions
│   └── calculations.py         # ALL deterministic quantity formulas
├── mto_boq/
│   ├── mto_generator.py        # Params -> MTO line items (calls engineering/)
│   ├── boq_generator.py        # MTO -> BOQ (rates, wastage, cost)
│   └── rates.py                # Default material/labour rate book (editable)
├── export/
│   ├── excel_export.py         # openpyxl workbook builder
│   └── pdf_export.py           # ReportLab PDF report builder
├── ui/
│   ├── state.py                # Streamlit session-state helpers
│   └── components.py           # Reusable UI widgets (editable tables etc.)
├── utils/
│   ├── helpers.py              # Small shared utilities
│   └── units.py                # SI <-> FPS display/input conversion layer
├── data/
│   ├── material_rates.json     # Default rate book (PKR, editable in-app)
│   └── default_assumptions.json# Default engineering assumptions
└── sample_data/                # (optional) sample drawing for demo
```

---

## 3a. Units & currency

The app always **calculates internally in SI/metric units** (m, m², m³, kg) -
that never changes. What the user sees is controlled by a per-project
**Unit System** toggle in Step 1:

- **SI (Metric)** - dimensions entered/shown in metres, m², m³.
- **FPS (Feet-Inch, Pakistani practice)** - dimensions entered/shown in feet
  (lengths/heights), inches (slab/wall thickness, column & beam
  cross-sections - matching how these are conventionally quoted on-site),
  square feet (areas) and cubic feet (concrete/excavation quantities in the
  MTO/BOQ). Steel is always quoted/priced in **kg** in either system, since
  that's how it's bought in Pakistan regardless of which system the rest of
  the job is measured in.

Switching the toggle never changes a single underlying number or the final
cost - it only changes how values are displayed and entered. The rate-book
editor (Step 5) shows/accepts rates per cft or sqft when FPS is selected,
but stores them internally per m³/m² so the BOQ math is identical either
way (see `utils/units.py` for the conversion functions and the invariant
this relies on: `display_quantity × display_rate == amount`, always).

The default rate book (`data/material_rates.json`) is priced in **PKR**,
built from published September-2026 Pakistani market prices for cement,
Grade-60 steel, sand, crush/bajri, bricks, plaster and paint, combined with
standard nominal-mix/dry-volume-factor quantities and typical site labour
allowances (see the `note` field in that file for the full breakdown). As
with everything else in this app, these are **indicative defaults only** -
always override them with your own current, local quotations before
relying on the cost estimate.

---

## 3b. Multi-file drawing upload (Plan / Elevation / Section)

Step 1 accepts up to `config.MAX_DRAWING_FILES` (default 3) separate
drawing files, each taggable as Plan / Elevation / Section / Other. This
matters because a Plan view is a horizontal slice - it cannot show vertical
dimensions at all. Adding a Section lets the AI actually read floor-to-floor
height, footing depth, and slab thickness instead of guessing defaults for
them; an Elevation is a good cross-check for floor count and overall height.
The tag you pick is passed straight into the AI prompt ("Image 1 = Plan,
Image 2 = Section, ...") so the model knows which kind of dimension to
expect from which image.

To keep any one analysis call within free-tier Groq limits, pages/images
are capped at `config.MAX_PAGES_PER_FILE` (default 2) per file and
`config.MAX_TOTAL_IMAGES` (default 6) in total across every uploaded file -
extra pages/files beyond the caps are silently dropped with an on-screen
notice, never a crash.

---

## 4. Local setup

```bash
git clone https://github.com/<your-username>/mto-boq-estimator.git
cd mto-boq-estimator

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Get a **free** Groq API key at https://console.groq.com/keys and set it as
an environment variable (never commit it):

```bash
export GROQ_API_KEY="gsk_..."          # macOS/Linux
setx GROQ_API_KEY "gsk_..."            # Windows
```

Run the app:

```bash
streamlit run app.py
```

The app also lets a user paste their own Groq API key into a sidebar field
at runtime (kept only in session memory) — handy for a shared public demo
deployment where you don't want to expose your own key/quota.

---

## 5. Deployment (100% free stack)

See **`DEPLOYMENT.md`** for the full step-by-step guide to:
1. Push this project to GitHub
2. Deploy on Streamlit Community Cloud (free tier)
3. Configure the `GROQ_API_KEY` secret
4. Common troubleshooting (package sizes, EasyOCR model downloads, etc.)

---

## 6. Engineering assumptions & thumb rules used

All defaults live in `engineering/rules.py` and `data/default_assumptions.json`
and are **editable from the UI**. Key thumb rules (typical Indian residential
RCC practice, adjust per local code/practice):

| Item | Thumb rule | Notes |
|---|---|---|
| Footing steel | 60–100 kg/m³ of footing concrete | isolated footing, editable |
| Column steel | 140–200 kg/m³ of column concrete | incl. main bars + ties |
| Beam steel | 110–160 kg/m³ of beam concrete | |
| Slab steel | 70–100 kg/m³ of slab concrete | one-way/two-way not distinguished in MVP |
| Excavation working space | +150 mm each side of footing | for shuttering/working |
| PCC thickness | 75 mm (default) | below footings |
| Concrete wastage | 3–5% | editable |
| Steel wastage | 3–5% | editable |
| Block/brick wastage | 5% | editable |
| Plaster thickness | 12 mm internal / 15–20 mm external | editable |
| Dry volume factor (wet→dry concrete) | 1.54 | standard factor for mix design qty |

These are **industry-typical preliminary/thumb-rule values**, not a
substitute for structural design. They are shown to the user with sources
in-app and are fully editable before the BOQ is generated.

---

## 7. Tech stack (all free/open-source)

- **Streamlit** — UI & app hosting (Community Cloud free tier)
- **Groq API** — free-tier LLM inference (vision-capable Llama model) for
  drawing interpretation
- **PyMuPDF (fitz)** — PDF parsing/rasterization
- **OpenCV** — image cleanup (deskew, contrast, resize)
- **EasyOCR** — optional OCR pass to help the LLM read dimension text
- **Pandas** — tabular data handling
- **Pydantic** — schema validation for all AI outputs and calculation results
- **OpenPyXL** — Excel export
- **ReportLab** — PDF export
- **SQLite** (optional, `utils/helpers.py` has a stub) — local project
  history persistence, disabled by default on Streamlit Cloud (ephemeral
  filesystem)

---

## 8. Roadmap ideas (post-MVP)

- Bar Bending Schedule (BBS) generation
- Multi-drawing (plan + elevation + section) cross-referencing
- MEP quantity modules
- Region-specific rate books (state-wise DSR import)
- User accounts + project history (Postgres/Supabase free tier)
- Automatic wall/room polygon detection from CV (contour + Hough lines)
- Confidence calibration using drawing scale detection
