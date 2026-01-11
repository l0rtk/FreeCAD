# PLAN.md - Cursor for Builders

## Vision

**Build the "Cursor for Builders"** - an AI-powered design platform that enables anyone to design structurally valid, code-compliant buildings through natural language.

```
"Create a 30m x 50m warehouse for heavy storage in seismic zone 2"
                              ↓
              [AI + FreeCAD + Eurocode Engine]
                              ↓
         Complete building design with calculations
```

---

## The Problem

### Current State of Construction Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TODAY'S PAINFUL WORKFLOW                             │
│                                                                             │
│   ARCHITECT              STRUCTURAL ENG.           DETAILER                 │
│   ┌─────────┐           ┌─────────┐              ┌─────────┐               │
│   │ "I want │           │ "That   │              │ Manual  │               │
│   │ this    │ ────────▶ │ won't   │ ────────▶   │ 500     │               │
│   │ design" │           │ work"   │              │ drawings│               │
│   └─────────┘           └─────────┘              └─────────┘               │
│        │                     │                        │                     │
│        │    WEEKS OF         │     WEEKS OF           │    WEEKS OF        │
│        │    BACK & FORTH     │     CALCULATIONS       │    DETAILING       │
│        ▼                     ▼                        ▼                     │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    TOTAL: 3-6 MONTHS                                 │  │
│   │                    COST: $50K-500K+ in design fees                   │  │
│   │                    ERRORS: Found during construction = $$$$$         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Current Tools Fail

| Tool | Problem |
|------|---------|
| **Revit/ArchiCAD** | Powerful but complex. No AI. No structural validation. $2,500+/year |
| **ETABS/Robot** | Analysis only. Doesn't design. Requires engineer expertise |
| **Tekla/ALLPLAN** | Detailing only. Expensive. Steep learning curve |
| **ChatGPT** | Knows theory but can't produce actual designs |

### The Gap

**Nobody has built a tool that:**
1. Takes natural language input
2. Generates 3D BIM model
3. Validates against building codes
4. Produces construction documents
5. Is affordable/accessible

---

## The Solution

### "Cursor for Builders" Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   USER INPUT                                                                │
│   "30x50m warehouse, heavy storage, precast, seismic zone 2"               │
│                              │                                              │
│                              ▼                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      AI DESIGN AGENT                                 │  │
│   │                                                                      │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │  │
│   │  │ Intent      │  │ Structural  │  │ Code        │                  │  │
│   │  │ Parser      │  │ Knowledge   │  │ Knowledge   │                  │  │
│   │  │             │  │             │  │             │                  │  │
│   │  │ "warehouse" │  │ span/depth  │  │ EN 1990     │                  │  │
│   │  │ "30x50m"    │  │ rules       │  │ EN 1991     │                  │  │
│   │  │ "precast"   │  │ precast     │  │ EN 1992     │                  │  │
│   │  │ "seismic"   │  │ catalog     │  │ EN 1998     │                  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                  │  │
│   │                              │                                       │  │
│   └──────────────────────────────┼───────────────────────────────────────┘  │
│                                  ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      FreeCAD BIM ENGINE                              │  │
│   │                                                                      │  │
│   │  • Generate 3D parametric model                                      │  │
│   │  • Columns, beams, slabs, walls, connections                         │  │
│   │  • Material properties, dimensions, positions                        │  │
│   │  • IFC-compliant structure                                           │  │
│   └──────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    EUROCODE CALCULATION ENGINE                       │  │
│   │                                                                      │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │ LOAD ANALYSIS (EN 1991)                                       │   │  │
│   │  │ • Dead loads (self-weight, finishes)                          │   │  │
│   │  │ • Live loads (storage, traffic)                               │   │  │
│   │  │ • Wind loads (terrain, building shape)                        │   │  │
│   │  │ • Snow loads (climate zone)                                   │   │  │
│   │  │ • Seismic loads (zone, soil, ductility)                       │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   │                              │                                       │  │
│   │                              ▼                                       │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │ STRUCTURAL ANALYSIS                                           │   │  │
│   │  │ • Frame analysis (forces, moments)                            │   │  │
│   │  │ • Load combinations (EN 1990)                                 │   │  │
│   │  │ • Critical load cases                                         │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   │                              │                                       │  │
│   │                              ▼                                       │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │ MEMBER DESIGN (EN 1992)                                       │   │  │
│   │  │ • Beam design (flexure, shear, deflection)                    │   │  │
│   │  │ • Column design (axial + bending, slenderness)                │   │  │
│   │  │ • Slab design (one-way, two-way)                              │   │  │
│   │  │ • Connection design (corbels, dowels)                         │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   │                              │                                       │  │
│   │                              ▼                                       │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │ VALIDATION & OPTIMIZATION                                     │   │  │
│   │  │ • Check utilization ratios (demand/capacity < 1.0)            │   │  │
│   │  │ • Flag over/under-designed members                            │   │  │
│   │  │ • Suggest size adjustments                                    │   │  │
│   │  │ • Update model with optimized sizes                           │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   └──────────────────────────────┬───────────────────────────────────────┘  │
│                                  ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         OUTPUT                                       │  │
│   │                                                                      │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│   │  │ 3D BIM      │  │ Calculation │  │ Shop        │  │ IFC        │  │  │
│   │  │ Model       │  │ Report      │  │ Drawings    │  │ Export     │  │  │
│   │  │             │  │             │  │             │  │            │  │  │
│   │  │ Visual      │  │ PDF with    │  │ Each panel  │  │ For Revit  │  │  │
│   │  │ review      │  │ all calcs   │  │ detailed    │  │ Tekla etc  │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why This Can Work

### 1. The AI Revolution
- LLMs can now understand complex technical requirements
- Code generation is mature (proven with software development)
- Structural engineering follows deterministic rules → automatable

### 2. Open Source Foundation
- **FreeCAD** = Free, mature, BIM-capable CAD platform
- **EurocodePy** = Python Eurocode calculations exist
- **PyNite/OpenSees** = Structural analysis engines available

### 3. Market Timing
- Construction industry desperate for productivity gains
- Labor shortage in engineering
- AI adoption accelerating

### 4. Defensible Position
- Building code knowledge is a moat
- Integration with FreeCAD is unique
- Training data from real projects creates advantage

---

## Phased Implementation

### Phase 1: MVP - Precast Warehouse Generator (Current Focus)

**Goal:** User describes warehouse → AI generates complete precast design with calculations

**Scope:**
```
INPUT:
  - Dimensions (length, width, height)
  - Usage (light storage, heavy storage, manufacturing)
  - Location (for climate and seismic)
  - Basic preferences (column-free span, door locations)

OUTPUT:
  - 3D FreeCAD model with:
    - Precast columns (sized per Eurocode)
    - Precast beams (sized per Eurocode)
    - Precast roof slabs or steel trusses
    - Precast wall panels
  - Calculation summary (member utilization)
  - Warning if any member fails

NOT IN SCOPE (Phase 1):
  - Foundations
  - Connections (use standard details)
  - Shop drawings
  - Full calculation report
```

**Technical Components:**

| Component | Description | Approach |
|-----------|-------------|----------|
| AI Assistant | Natural language interface | Done (Nakle API) |
| Structural Rules | Sizing heuristics | Add to system prompt |
| Precast Catalog | Standard sections | JSON data file |
| Basic Eurocode | Load combinations, utilization | Python module |
| FreeCAD Integration | Generate model | Done (basic) |

**Success Criteria:**
- [ ] User can describe warehouse in plain English
- [ ] AI generates structurally reasonable model
- [ ] Member sizes are within 20% of hand calculation
- [ ] Process takes < 5 minutes vs hours manually

---

### Phase 2: Eurocode Calculation Engine

**Goal:** Full code-compliant structural calculations

**Components:**

```
eurocode/
├── __init__.py
├── en1990/                    # Basis of structural design
│   ├── load_combinations.py   # ULS, SLS combinations
│   └── partial_factors.py     # γG, γQ, γM factors
├── en1991/                    # Actions on structures
│   ├── dead_loads.py          # Self-weight calculations
│   ├── live_loads.py          # Imposed loads by category
│   ├── wind_loads.py          # Wind pressure calculation
│   ├── snow_loads.py          # Snow load by zone
│   └── seismic/               # EN 1998
│       ├── response_spectrum.py
│       └── design_spectrum.py
├── en1992/                    # Concrete design
│   ├── materials.py           # Concrete, steel properties
│   ├── beam_design.py         # Flexure, shear, deflection
│   ├── column_design.py       # Axial + bending, slenderness
│   ├── slab_design.py         # One-way, two-way
│   └── precast/
│       ├── corbel_design.py
│       ├── connection_design.py
│       └── handling_check.py  # Lifting, transport
├── analysis/
│   ├── frame_analysis.py      # Using PyNite
│   └── load_distribution.py
└── reports/
    ├── calculation_report.py  # PDF generation
    └── templates/
```

**Key Eurocode Formulas to Implement:**

```python
# EN 1992-1-1: Beam flexural design
def design_beam_flexure(M_Ed, b, d, fck, fyk):
    """
    M_Ed: Design bending moment (kNm)
    b: Width (mm)
    d: Effective depth (mm)
    fck: Concrete characteristic strength (MPa)
    fyk: Steel yield strength (MPa)

    Returns: Required reinforcement As (mm²)
    """
    fcd = fck / 1.5  # Design concrete strength
    fyd = fyk / 1.15  # Design steel strength

    # Normalized moment
    mu = M_Ed * 1e6 / (b * d**2 * fcd)

    # Lever arm
    if mu <= 0.295:  # Singly reinforced
        z = d * (0.5 + sqrt(0.25 - mu/1.134))
        As = M_Ed * 1e6 / (z * fyd)
    else:
        raise ValueError("Section requires compression reinforcement")

    return As

# EN 1991-1-1: Imposed loads
IMPOSED_LOADS = {
    "A": 2.0,      # Residential
    "B": 3.0,      # Office
    "C": 5.0,      # Assembly
    "D": 5.0,      # Shopping
    "E1": 7.5,     # Storage (general)
    "E2": 15.0,    # Industrial storage
}

# EN 1990: Load combinations (ULS)
def uls_combination(G, Q, W=0, S=0):
    """
    G: Permanent load
    Q: Leading variable (imposed)
    W: Wind
    S: Snow
    """
    combinations = [
        1.35*G + 1.5*Q + 1.5*0.6*W + 1.5*0.5*S,  # Imposed leading
        1.35*G + 1.5*W + 1.5*0.7*Q + 1.5*0.5*S,  # Wind leading
        1.35*G + 1.5*S + 1.5*0.7*Q + 1.5*0.6*W,  # Snow leading
    ]
    return max(combinations)
```

---

### Phase 3: Intelligent Design Assistant

**Goal:** AI that iterates and improves designs

**Features:**

```
CONVERSATIONAL DESIGN:
┌────────────────────────────────────────────────────────────────────┐
│ User: Create a 40x60m warehouse                                    │
│                                                                    │
│ AI: I've created an initial design with:                          │
│     - 8m x 10m column grid (5x7 columns)                          │
│     - 600x400 precast beams (10m span)                            │
│     - 265mm hollow core slabs                                      │
│                                                                    │
│     ⚠️ Note: The corner columns are at 95% utilization.           │
│     Would you like me to increase them to 600x600?                │
│                                                                    │
│ User: Yes, and can we have a 15m clear span in the middle?        │
│                                                                    │
│ AI: For a 15m span, I'll need to use:                             │
│     - Prestressed I-beams (800mm deep) instead of rectangular     │
│     - Columns increased to 700x700 for the higher loads           │
│                                                                    │
│     This adds approximately 15% to the structural cost.           │
│     Should I proceed?                                              │
│                                                                    │
│ User: Show me both options side by side                           │
│                                                                    │
│ AI: [Generates comparison view with cost/weight estimates]        │
└────────────────────────────────────────────────────────────────────┘
```

**Capabilities:**
- Design iteration based on feedback
- Trade-off analysis (cost vs performance)
- Alternative suggestions
- Constraint satisfaction (headroom, loading dock access)

---

### Phase 4: Shop Drawing Generation

**Goal:** Auto-generate fabrication drawings for each piece

**Output per precast element:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    PRECAST BEAM B-12                            │
│                    Drawing No: PRJ-001-B12-01                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    [ELEVATION VIEW]                                             │
│    ┌──────────────────────────────────────────────────┐        │
│    │  ○────○────○────○────○────○────○────○────○────○  │        │
│    │  │                                            │  │        │
│    │  │                                            │  │        │
│    └──┴────────────────────────────────────────────┴──┘        │
│    ◄─────────────── 6000 mm ───────────────────────►           │
│                                                                 │
│    [SECTION A-A]           [SECTION B-B]                       │
│    ┌────────┐              ┌────────┐                          │
│    │ ○    ○ │              │ ○    ○ │                          │
│    │        │   400        │    ◯   │                          │
│    │ ○    ○ │              │ ○    ○ │                          │
│    └────────┘              └────────┘                          │
│      300                     300                                │
│                                                                 │
│    REINFORCEMENT:                                              │
│    Main bars: 4Ø20 top, 4Ø25 bottom                           │
│    Stirrups: Ø10@150 (ends), Ø10@200 (middle)                 │
│    Concrete: C40/50                                            │
│    Cover: 35mm                                                 │
│                                                                 │
│    LIFTING: 2x Deha 20t anchors @ 1200mm from ends            │
│    WEIGHT: 2.8 tonnes                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: Full Platform

**Features:**
- Multi-user collaboration
- Project management
- Revision tracking
- Cost estimation integration
- Contractor bidding portal
- As-built documentation

---

## Technical Stack

### Current (MVP)

```
┌─────────────────────────────────────────────────────────────────┐
│                         CURRENT STACK                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UI Layer           FreeCAD + Qt (PySide6)                     │
│                     AIAssistant dock panel                      │
│                                                                 │
│  AI Layer           Nakle API (Claude)                         │
│                     Custom system prompt                        │
│                                                                 │
│  CAD Engine         FreeCAD (Part, Arch, BIM modules)          │
│                     Python scripting                            │
│                                                                 │
│  Data               In-memory FreeCAD document                 │
│                     JSON export                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Target (Full Platform)

```
┌─────────────────────────────────────────────────────────────────┐
│                         TARGET STACK                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend           FreeCAD desktop (power users)              │
│                     Web viewer (stakeholders)                   │
│                     Mobile app (site access)                    │
│                                                                 │
│  AI Layer           Nakle API + Custom fine-tuned model        │
│                     RAG for building codes                      │
│                     Multi-agent (design, calc, drawing)        │
│                                                                 │
│  Calculation        Custom Eurocode engine (Python)            │
│  Engine             PyNite/OpenSees for analysis               │
│                     SymPy for symbolic math                    │
│                                                                 │
│  CAD Engine         FreeCAD (core modeling)                    │
│                     Custom precast library                      │
│                     TechDraw for drawings                       │
│                                                                 │
│  Backend            FastAPI                                     │
│                     PostgreSQL + PostGIS                        │
│                     Redis (caching)                             │
│                     S3 (file storage)                           │
│                                                                 │
│  Infrastructure     Docker/Kubernetes                          │
│                     CI/CD pipeline                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Competitive Landscape

### Direct Competitors

| Company | Approach | Weakness |
|---------|----------|----------|
| **TestFit** | AI for site planning | No structural, architecture only |
| **Higharc** | AI home design | Residential only, no engineering |
| **Spacemaker** (Autodesk) | Site optimization | High-level only, no detailed design |
| **Alice Technologies** | Construction scheduling | Not design, just scheduling |

### Indirect Competitors

| Company | Product | Our Advantage |
|---------|---------|---------------|
| **Autodesk** | Revit | Expensive, no AI, steep learning curve |
| **Trimble** | Tekla | Expensive, detailing only |
| **ALLPLAN** | Precast | Very expensive, limited AI |
| **Bentley** | Various | Enterprise complexity |

### Our Position

```
                        MARKET POSITIONING

        Low Cost ◄─────────────────────────────► High Cost
                          │
        ┌─────────────────┼─────────────────────────────┐
        │                 │                             │
   Full │    ★ US        │                   Tekla     │
   Auto │   (Target)      │                   ALLPLAN   │
        │                 │                             │
        ├─────────────────┼─────────────────────────────┤
        │                 │                             │
Partial │   TestFit       │              Revit          │
   Auto │   Higharc       │              ArchiCAD       │
        │                 │                             │
        ├─────────────────┼─────────────────────────────┤
        │                 │                             │
 Manual │   FreeCAD       │              AutoCAD        │
        │   SketchUp      │                             │
        │                 │                             │
        └─────────────────┴─────────────────────────────┘
```

---

## Go-to-Market

### Target Users (Phase 1)

1. **Small precast manufacturers** (10-50 employees)
   - Pain: Can't afford Tekla/ALLPLAN
   - Value: Faster quotation, automated detailing

2. **Structural engineering firms** (1-10 engineers)
   - Pain: Repetitive calculations for similar buildings
   - Value: 10x faster preliminary design

3. **Design-build contractors**
   - Pain: Coordination between architect/engineer
   - Value: Single tool for both

### Pricing Model

```
FREE TIER:
  - Basic AI assistant
  - Manual modeling in FreeCAD
  - Export to IFC

PRO ($99/month):
  - Eurocode calculation engine
  - Precast warehouse generator
  - Calculation reports

ENTERPRISE (Custom):
  - Multi-user
  - Custom catalogs
  - API access
  - Training
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Liability** - AI makes structural error | Critical | Disclaimer, engineer review required, conservative factors |
| **Accuracy** - Calculations wrong | High | Extensive testing, comparison with commercial software |
| **Adoption** - Engineers don't trust AI | Medium | Transparent calculations, show all assumptions |
| **Competition** - Autodesk adds AI to Revit | High | Move fast, build code knowledge moat |
| **Regulation** - Some countries require licensed software | Medium | Partner with local engineering firms |

---

## Immediate Next Steps

### Week 1-2: Enhanced AI Assistant
- [ ] Add structural sizing rules to system prompt
- [ ] Create precast catalog (JSON with standard sections)
- [ ] Test with "create warehouse" prompts
- [ ] Validate generated designs manually

### Week 3-4: Basic Calculation Module
- [ ] Implement EN 1990 load combinations
- [ ] Implement EN 1991 basic loads (dead, live, wind)
- [ ] Implement EN 1992 beam/column utilization check
- [ ] Connect to FreeCAD model

### Week 5-6: Integration & Testing
- [ ] AI generates model → Calculation validates
- [ ] Feedback loop (if fails → AI adjusts)
- [ ] Create 5 test cases (small/medium/large warehouses)
- [ ] Compare with hand calculations

### Week 7-8: MVP Polish
- [ ] Calculation summary in UI
- [ ] Warning/error display
- [ ] Basic PDF report
- [ ] Documentation

---

## Success Metrics

### MVP Success
- [ ] Generate warehouse design in < 5 minutes
- [ ] Member utilization within ±20% of manual calc
- [ ] 80% of test cases pass structural checks
- [ ] 3 beta users provide positive feedback

### 6-Month Goals
- [ ] 100 active users
- [ ] 10 paying customers
- [ ] Full Eurocode 2 beam/column design
- [ ] Shop drawing generation for simple elements

### 12-Month Goals
- [ ] 1,000 active users
- [ ] 100 paying customers
- [ ] Seismic design (EN 1998)
- [ ] Foundation design
- [ ] Multi-material (steel + concrete)

---

## The Vision

```
TODAY (Hours/Days):
┌─────────────────────────────────────────────────────────────────┐
│  Architect:     "I want a 40x60m warehouse"                     │
│  (draws for 2 weeks)                                            │
│                                                                 │
│  Engineer:      "The spans are too long, columns too small"     │
│  (recalculates for 2 weeks)                                     │
│                                                                 │
│  Detailer:      "Here are 347 shop drawings"                    │
│  (draws for 4 weeks)                                            │
│                                                                 │
│  Total: 8+ weeks, $50,000+ in fees                             │
└─────────────────────────────────────────────────────────────────┘

TOMORROW (Minutes):
┌─────────────────────────────────────────────────────────────────┐
│  User:          "Create a 40x60m warehouse for heavy storage    │
│                  in Berlin, precast construction"               │
│                                                                 │
│  AI:            "Here's your design:                            │
│                  - 45 precast columns (500x500)                 │
│                  - 72 precast beams (400x600)                   │
│                  - 180 hollow core slabs (265mm)                │
│                  - All members pass EN 1992 checks              │
│                  - Estimated cost: €2.3M                        │
│                  - Calculation report attached"                 │
│                                                                 │
│  Total: 5 minutes, validated design ready for review           │
└─────────────────────────────────────────────────────────────────┘
```

**This is the future we're building.**

---

*Last updated: 2026-01-11*
*Version: 0.1*
