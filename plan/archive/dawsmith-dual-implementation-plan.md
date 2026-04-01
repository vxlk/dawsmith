# DAWsmith: Dual Implementation Plan

## Project Identity

**Name**: DAWsmith
**Tagline**: The open-source Python engine for programmatic music production.
**Namespace**: `dawsmith` (PyPI), `dawsmith` (GitHub org)

---

## 1. The Split

DAWsmith is two codebases with a clean boundary between them.

### Open Source: `dawsmith` (GPLv3)

The Python bindings around Tracktion Engine, the data model, the DAW format exporters, and the validation suite. This is the engine — the thing that creates, renders, and exports music programmatically. Anyone can use it, extend it, and build on it.

**Repository**: `github.com/dawsmith/dawsmith`

Contains:
- nanobind Python bindings for Tracktion Engine (Edit, Track, Clip, Plugin, Transport, Render)
- Data model API (`dawsmith.Edit`, `dawsmith.Track`, `dawsmith.MidiClip`, etc.)
- Built-in plugin wrappers (reverb, compressor, EQ, tone generator)
- VST3/AU/CLAP plugin hosting interface
- Offline rendering to WAV/stems
- Edit XML save/load (native Tracktion format)
- DAWproject export
- REAPER RPP export
- Ableton ALS export (basic)
- FL Studio FLP export
- MIDI export
- Metadata export (JSON/Parquet)
- Validation suite (tempo detection, key detection, spectral analysis, RMS, clipping, band energy)
- MIR utilities (chromagram, onset detection, beat tracking)
- Batch runner (parallel rendering)
- Documentation, examples, tutorials
- Full test suite

**License**: GPLv3 (matching Tracktion Engine)

### Proprietary: `dawsmith-pro` (Commercial)

The intelligence layer — genre templates, the evaluation loop, the agent integration, the auto-generation logic, and the cloud API. This is what turns the engine into a data generation product. This is where the institutional knowledge, the musical expertise, and the competitive moat live.

**Repository**: `github.com/dawsmith/dawsmith-pro` (private)

Contains:
- Genre template library (30+ parameterized arrangement generators)
- Evaluation loop engine (spec → render → validate → fix → re-render → export)
- Reference analysis pipeline (extract tempo/key/structure/spectral profile from reference audio)
- Specification system (structured JSON/YAML specs defining target musical properties)
- Auto-generation logic (translate specs into Edit arrangements)
- Constraint solver (ensure musical correctness — notes in key, ranges valid, structure coherent)
- Agent integration layer (tool-use interface for LLM agents)
- Dataset generation orchestrator (spec → N variations → validated output → packaged dataset)
- Cloud API server (REST API for hosted rendering + generation)
- Pre-built plugin parameter databases (preset → parameter mappings)
- Quality scoring system (multi-metric scoring beyond pass/fail validation)
- A/B comparison tools (compare two renders against a reference)
- Reporting and analytics (dataset statistics, generation success rates)

**License**: Proprietary / Commercial

---

## 2. The Boundary

The boundary between open and proprietary must be clean, enforceable, and intuitive to developers.

### The Rule

**dawsmith (open)** answers: "I have a complete musical description. Render it, validate it, export it."

**dawsmith-pro (proprietary)** answers: "I have a vague intent. Figure out the musical description, generate it, evaluate it, iterate until it's correct, and package the result."

### In Code

```python
# === This is dawsmith (open source) ===
import dawsmith as ds

engine = ds.Engine("MyApp")
edit = ds.Edit.create(engine, bpm=65, key="D", time_signature=(4, 4))

drums = edit.insert_audio_track("Drums")
drums.insert_plugin("builtin:drumkit")
clip = drums.insert_midi_clip("verse", start_beat=0, length_beats=32)
clip.add_note(36, start_beat=0, length_beats=0.5, velocity=127)
clip.add_note(38, start_beat=2, length_beats=0.25, velocity=100)
# ... (user writes the full arrangement manually)

edit.render("output.wav")
validation = ds.validate(edit, "output.wav")  # returns pass/fail metrics
edit.export_dawproject("output.dawproject")
edit.export_midi("output.mid")
edit.export_metadata("output.json")

# === This is dawsmith-pro (proprietary) ===
from dawsmith_pro import generate, evaluate, dataset

# Generate from a spec
spec = dataset.Spec(
    genre="doom_metal",
    bpm_range=(55, 75),
    key="D",
    duration_seconds=180,
    tracks=["drums", "guitar", "bass"],
    reference_audio="electric_wizard_clip.wav"  # optional
)

# Auto-generate: creates the Edit, renders, validates, iterates
result = generate(spec, engine, max_iterations=10)
# result.edit      — the final Edit object (dawsmith open source)
# result.audio     — rendered WAV
# result.stems     — per-track stems
# result.metadata  — full annotations
# result.exports   — dict of format → filepath
# result.score     — quality score (0-100)
# result.log       — iteration history

# Generate a dataset
dataset.generate_batch(
    specs=[spec.randomize(seed=i) for i in range(10000)],
    output_dir="./training_data/",
    formats=["wav", "stems", "dawproject", "midi", "metadata"],
    workers=8
)
```

### The Interface Contract

`dawsmith-pro` depends on `dawsmith`. It imports `dawsmith` as a library and builds on top of it. The open-source library has no knowledge of or dependency on the proprietary layer.

```
dawsmith-pro (proprietary)
    │
    │  imports and builds on
    │
    ▼
dawsmith (open source, GPLv3)
    │
    │  wraps via nanobind
    │
    ▼
Tracktion Engine (C++, GPL/Commercial)
    │
    │  built on
    │
    ▼
JUCE (C++, GPL/Commercial)
```

The open-source layer is fully functional on its own. A user who never touches dawsmith-pro can still create edits, render audio, validate, and export to every format. They just have to write their own arrangement logic and generation pipelines.

---

## 3. What Stays Open vs. What Goes Proprietary

### Decision Framework

For each feature, ask: **Does this enable the engine to work, or does it make the engine smart?**

Engine functionality → open source. Intelligence/automation → proprietary.

| Feature | Open or Pro | Rationale |
|---|---|---|
| Python bindings for Tracktion Engine | Open | Engine functionality — the core platform |
| Edit/Track/Clip/Plugin data model | Open | Engine functionality |
| Audio rendering | Open | Engine functionality |
| VST/AU/CLAP plugin hosting | Open | Engine functionality |
| MIDI import/export | Open | Engine functionality |
| DAWproject/ALS/RPP/FLP export | Open | Engine functionality — format serialization |
| Metadata export (JSON/Parquet) | Open | Engine functionality — data serialization |
| Validation suite (tempo, key, RMS, spectral metrics) | Open | Engine functionality — the validators are measurement tools |
| MIR utilities (librosa wrappers) | Open | Engine functionality — standard analysis |
| Batch runner (parallel rendering) | Open | Engine functionality — parallelism is infrastructure |
| Genre templates | **Pro** | Intelligence — musical knowledge encoded as generation logic |
| Evaluation loop (render → validate → fix → iterate) | **Pro** | Intelligence — the autonomous correction loop |
| Reference analysis (extract features from audio) | **Pro** | Intelligence — turns audio into actionable specs |
| Specification system | **Pro** | Intelligence — the structured intent language |
| Auto-generation (spec → arrangement) | **Pro** | Intelligence — the core generation logic |
| Constraint solver | **Pro** | Intelligence — musical correctness enforcement |
| Agent integration (LLM tool-use interface) | **Pro** | Intelligence — agent orchestration |
| Dataset orchestrator | **Pro** | Intelligence — batch generation with quality control |
| Cloud API | **Pro** | Infrastructure — hosted service |
| Plugin parameter database | **Pro** | Intelligence — curated knowledge base |
| Quality scoring (beyond pass/fail) | **Pro** | Intelligence — nuanced evaluation |

### Gray Areas

**Validation suite**: The basic validators (tempo detection, RMS, clipping) are open because they're standard MIR measurements. The *evaluation loop* that uses those validators to iteratively improve a render is proprietary — that's the intelligence layer.

**One example template**: Ship ONE simple genre template in the open-source repo as a demonstration (e.g., a basic 4-bar drum loop generator). This proves the API works end-to-end and shows developers how to build their own templates. The full library of 30+ production-quality templates is proprietary.

**Batch runner**: The basic parallel renderer is open (it's just "render N edits across M cores"). The dataset orchestrator that generates randomized specs, validates outputs, retries failures, and packages results into training datasets is proprietary.

---

## 4. Business Model

### 4.1 Revenue Streams

| Stream | Source | Pricing |
|---|---|---|
| **dawsmith-pro licenses** | Individual developers, small teams | $29/month or $249/year |
| **dawsmith-pro team** | Startups, research labs (up to 10 seats) | $99/month or $899/year |
| **Enterprise** | AI music companies, large research organizations | $5K-50K/year (custom) |
| **Cloud API** | Per-render pricing for hosted generation | $0.005-0.05 per render |
| **Datasets** | Pre-generated annotated multi-track datasets | $10K-100K per dataset |
| **Consulting** | Custom template development, integration work | $200-400/hour |

### 4.2 Free vs. Paid Feature Matrix

| Capability | dawsmith (Free/GPL) | dawsmith-pro |
|---|---|---|
| Create edits, tracks, clips programmatically | ✓ | ✓ |
| Render to WAV/stems | ✓ | ✓ |
| Host VST3/AU/CLAP plugins | ✓ | ✓ |
| Export to DAWproject/ALS/RPP/MIDI | ✓ | ✓ |
| Export metadata (JSON/Parquet) | ✓ | ✓ |
| Validation suite (tempo, key, spectral) | ✓ | ✓ |
| Batch parallel rendering | ✓ | ✓ |
| 1 example template | ✓ | ✓ |
| 30+ genre templates | | ✓ |
| Auto-generation from specs | | ✓ |
| Evaluation loop (render → validate → iterate) | | ✓ |
| Reference audio analysis | | ✓ |
| Agent integration (LLM tool-use) | | ✓ |
| Dataset generation orchestrator | | ✓ |
| Plugin parameter database | | ✓ |
| Quality scoring system | | ✓ |
| Cloud API access | | ✓ |
| Priority support | | ✓ |

### 4.3 Why People Pay

The open-source engine is powerful but manual. You have to write every note, every parameter, every arrangement decision yourself. That's fine for:
- Developers integrating audio rendering into their own pipelines
- Researchers who need precise control over every variable
- Hobbyists exploring programmatic music

But for the primary revenue use cases — generating training datasets at scale, prototyping arrangements quickly, agent-assisted production — writing every note by hand defeats the purpose. The proprietary layer is where "give me 10,000 doom metal tracks" becomes a single function call.

### 4.4 Pricing Philosophy

The open-source engine is genuinely free and fully functional — not crippled. This builds trust, drives adoption, and creates the ecosystem. The proprietary layer is genuinely valuable — not a paywall around basic features. It represents months of musical knowledge encoding, evaluation logic development, and infrastructure work that the open-source user doesn't have to do themselves.

---

## 5. Development Structure

### 5.1 Repository Layout

```
github.com/dawsmith/
├── dawsmith/                    # PUBLIC — open source (GPLv3)
│   ├── src/
│   │   ├── bindings/            # nanobind C++ ↔ Python
│   │   ├── dawsmith/            # Python package
│   │   │   ├── __init__.py
│   │   │   ├── engine.py        # Engine wrapper
│   │   │   ├── edit.py          # Edit wrapper
│   │   │   ├── track.py         # Track wrapper
│   │   │   ├── clip.py          # Clip wrappers (Audio, MIDI)
│   │   │   ├── plugin.py        # Plugin wrapper
│   │   │   ├── automation.py    # Automation curves
│   │   │   ├── transport.py     # Transport controls
│   │   │   ├── render.py        # Rendering interface
│   │   │   ├── validate.py      # Validation suite
│   │   │   ├── mir.py           # MIR utilities
│   │   │   ├── export/          # Format exporters
│   │   │   │   ├── dawproject.py
│   │   │   │   ├── reaper.py
│   │   │   │   ├── ableton.py
│   │   │   │   ├── flstudio.py
│   │   │   │   ├── midi.py
│   │   │   │   └── metadata.py
│   │   │   └── batch.py         # Parallel batch runner
│   │   └── tracktion_engine/    # C++ submodule
│   ├── tests/                   # Full test suite (from testing plan)
│   ├── examples/
│   │   ├── hello_world.py       # Minimal example
│   │   ├── midi_composition.py  # MIDI note composition
│   │   ├── multi_track_mix.py   # Multi-track mixing
│   │   ├── export_all.py        # Export to every format
│   │   ├── validate_render.py   # Validation example
│   │   └── simple_template.py   # ONE example template (basic drum loop)
│   ├── docs/
│   ├── CMakeLists.txt
│   ├── pyproject.toml
│   ├── LICENSE                  # GPLv3
│   └── README.md
│
├── dawsmith-pro/                # PRIVATE — proprietary
│   ├── src/
│   │   └── dawsmith_pro/
│   │       ├── __init__.py
│   │       ├── templates/       # Genre template library
│   │       │   ├── base.py      # Base template class
│   │       │   ├── doom_metal.py
│   │       │   ├── pop.py
│   │       │   ├── electronic.py
│   │       │   ├── jazz.py
│   │       │   ├── hip_hop.py
│   │       │   └── ...          # 30+ genres
│   │       ├── generate.py      # Auto-generation from specs
│   │       ├── evaluate.py      # Evaluation loop engine
│   │       ├── reference.py     # Reference audio analysis
│   │       ├── spec.py          # Specification system
│   │       ├── constraints.py   # Musical constraint solver
│   │       ├── agent.py         # LLM agent integration
│   │       ├── dataset.py       # Dataset generation orchestrator
│   │       ├── scoring.py       # Quality scoring system
│   │       ├── presets/         # Plugin parameter databases
│   │       └── api/             # Cloud API server
│   │           ├── server.py
│   │           ├── routes.py
│   │           └── workers.py
│   ├── tests/
│   ├── LICENSE                  # Proprietary
│   └── pyproject.toml           # depends on dawsmith
│
└── dawsmith.com/                # PRIVATE — website, docs, marketing
    ├── landing/
    ├── docs/
    ├── blog/
    └── api-docs/
```

### 5.2 Dependency Direction

```
dawsmith-pro
    │
    │  pip install dawsmith  (public dependency)
    │
    ▼
dawsmith ──── never imports dawsmith-pro
```

The open-source package must never import, reference, or conditionally check for the proprietary package. No "if dawsmith_pro is installed, unlock features" pattern. The two packages are independent from dawsmith's perspective. dawsmith-pro is just another user of the dawsmith API.

### 5.3 Development Workflow

**For dawsmith (open source)**:
- Public GitHub repo with issues, PRs, discussions
- CI/CD runs full test suite on every PR
- Community contributions welcome (under CLA — Contributor License Agreement)
- Releases to PyPI as `dawsmith`
- Changelog and semver versioning
- Public roadmap

**For dawsmith-pro (proprietary)**:
- Private GitHub repo
- Mirrors dawsmith's CI/CD patterns but adds proprietary test layers
- Internal team only (no external PRs)
- Distributed via private PyPI index or direct download with license key
- Releases track dawsmith versions (dawsmith-pro 0.3.x works with dawsmith 0.3.x)

### 5.4 Version Coupling

dawsmith-pro pins to a compatible range of dawsmith:

```toml
# dawsmith-pro/pyproject.toml
[project]
dependencies = [
    "dawsmith>=0.3.0,<0.4.0",
]
```

When dawsmith makes a breaking change (major version bump), dawsmith-pro has a migration window. Internal CI tests dawsmith-pro against dawsmith `main` nightly to catch breaking changes early.

---

## 6. Intellectual Property Strategy

### 6.1 Contributor License Agreement (CLA)

All contributors to the open-source dawsmith repo sign a CLA granting the DAWsmith organization (your company/entity) a perpetual, irrevocable license to use their contributions under any license — including proprietary. This is standard practice for open-core companies (MongoDB, Elastic, etc.) and is necessary because:

- You need to distribute dawsmith under GPLv3 for the community
- You need to use dawsmith code internally in dawsmith-pro without GPL contamination
- You may need to offer dawsmith under a commercial license to enterprise customers who can't use GPL

The CLA doesn't take copyright from contributors — it grants you a parallel license to use their work.

### 6.2 Commercial License for dawsmith

Some enterprise customers can't use GPL software in their products. Offer dawsmith under a dual license:

- **GPLv3**: Free, open source, standard open-source terms
- **Commercial**: Paid, allows proprietary derivative works, no copyleft obligation

This mirrors JUCE's and Tracktion Engine's own licensing model. The commercial license is a separate revenue stream from dawsmith-pro.

### 6.3 Trademark

Register "DAWsmith" as a trademark. Open-source projects can be forked (that's the point), but the name and branding remain yours. This prevents forks from trading on your reputation.

### 6.4 Trade Secrets in dawsmith-pro

The genre templates, evaluation logic, and generation algorithms in dawsmith-pro are trade secrets. They're never published, never open-sourced, and access requires a commercial license agreement. The musical knowledge encoded in the templates (how to generate a convincing doom metal arrangement, what parameter ranges sound right for each genre, how to evaluate "correctness" for each style) is the core competitive moat.

---

## 7. Community Strategy

### 7.1 Open Source Community

**Goal**: dawsmith becomes the standard Python library for programmatic music production, regardless of whether users buy dawsmith-pro.

**Tactics**:
- Excellent documentation with real-world examples
- Active GitHub Discussions for Q&A
- Discord server for real-time community
- Conference talks (ISMIR, AES, PyCon, ADC)
- Blog posts showing interesting use cases
- "Built with DAWsmith" showcase
- Responsive issue triage (< 48 hour first response)
- Regular releases (monthly minor, quarterly major)
- Public roadmap with community voting on features

**Contributor funnel**:
1. User discovers dawsmith, uses it for a project
2. User files a bug or feature request
3. User submits a PR (signs CLA)
4. Regular contributors get recognized (CONTRIBUTORS.md, Discord role)
5. Top contributors may be invited to join the core team or consult

### 7.2 Relationship Between Open and Pro Communities

Be transparent about the split. The README says:

> DAWsmith is free and open-source. For automated generation, evaluation loops, genre templates, and dataset tooling, see [dawsmith-pro](https://dawsmith.com/pro).

Never hide the existence of the commercial product. Never make the open-source project feel like a demo. People respect honest open-core models; they resent bait-and-switch.

### 7.3 What the Community Gets

The community benefits from the open-source engine regardless of dawsmith-pro:
- Researchers get a `pip install`-able DAW engine for their experiments
- Developers get programmatic DAW project file generation
- Hobbyists get a way to make music with Python
- Tool builders get a foundation to build their own automation on

dawsmith-pro is for the specific use case of "generate music at scale with quality control." Most open-source users won't need it. The ones who do are exactly the B2B customers you want.

---

## 8. Development Timeline (Revised for Dual Implementation)

### Phase 1: dawsmith Core (Months 1-4)

Focus entirely on the open-source engine. No dawsmith-pro work yet.

**Deliverables**:
- [ ] nanobind bindings: Engine, Edit, Track, Clip, Plugin, Render
- [ ] Built-in plugin wrappers
- [ ] Offline render to WAV/stems
- [ ] Basic validation suite
- [ ] `pip install dawsmith` on Linux
- [ ] 5 examples
- [ ] Test suite (Layer 0-2 from testing plan)
- [ ] GitHub repo public, README, basic docs

**dawsmith-pro**: Not started. All effort on the foundation.

### Phase 2: Export Layer + Pro Alpha (Months 4-7)

Open-source export layer ships. dawsmith-pro development begins in private.

**dawsmith deliverables**:
- [ ] DAWproject export
- [ ] REAPER RPP export
- [ ] MIDI export
- [ ] Metadata export (JSON/Parquet)
- [ ] Ableton ALS export (basic)
- [ ] VST3/AU plugin hosting
- [ ] macOS + Windows support
- [ ] Test suite (Layer 3-4 from testing plan)
- [ ] Documentation site
- [ ] 1 example template in open repo

**dawsmith-pro deliverables** (private):
- [ ] Specification system (Spec class, JSON/YAML parsing)
- [ ] 5 genre templates (doom metal, pop, electronic, hip hop, ambient)
- [ ] Basic evaluation loop (render → validate → retry)
- [ ] Reference audio analysis (tempo, key, spectral profile extraction)
- [ ] Internal test suite
- [ ] Private alpha with 2-3 trusted design partners

### Phase 3: Pro Beta + Scale (Months 7-12)

dawsmith stabilizes. dawsmith-pro reaches beta with paying customers.

**dawsmith deliverables**:
- [ ] FL Studio FLP export
- [ ] Batch parallel runner
- [ ] Performance optimization
- [ ] Test suite (Layer 5 from testing plan)
- [ ] Community building (conference talks, blog posts)
- [ ] First community contributions merged

**dawsmith-pro deliverables**:
- [ ] 15+ genre templates
- [ ] Agent integration layer (LLM tool-use interface)
- [ ] Dataset generation orchestrator
- [ ] Constraint solver (musical correctness)
- [ ] Quality scoring system
- [ ] Plugin parameter database (initial set)
- [ ] Cloud API beta
- [ ] Pricing and licensing in place
- [ ] Public launch of dawsmith-pro
- [ ] First paying customers

### Phase 4: Growth (Months 12-24)

**dawsmith**: Ecosystem growth, community-driven features, stability.
**dawsmith-pro**: Revenue growth, enterprise customers, dataset products.

---

## 9. Financial Projections

### Cost Structure

| Item | Monthly Cost | Notes |
|---|---|---|
| Engineering (1-2 people) | $15-25K | Salary/contractor cost |
| Cloud infrastructure (CI/CD) | $500-1K | GitHub Actions, build runners |
| Cloud API infrastructure | $1-3K | Starts Phase 3 |
| Legal (CLA, trademark, licensing) | $500 (amortized) | Front-loaded in Phase 1 |
| Domain, hosting, tools | $200 | dawsmith.com, monitoring |
| **Total** | **$17-30K/month** | |

### Revenue Projections

| | Month 6 | Month 12 | Month 18 | Month 24 |
|---|---|---|---|---|
| dawsmith GitHub stars | 500 | 2,000 | 4,000 | 8,000 |
| dawsmith monthly users | 100 | 500 | 1,500 | 3,000 |
| dawsmith-pro subscribers | 0 | 20 | 100 | 300 |
| Enterprise customers | 0 | 2 | 5 | 12 |
| Cloud API customers | 0 | 0 | 5 | 20 |
| **Monthly revenue** | **$0** | **$8K** | **$35K** | **$100K** |

Break-even at ~Month 14-16 depending on team size.

---

## 10. Risks Specific to Dual Model

### Risk: GPL Contamination

**Concern**: dawsmith is GPLv3. If dawsmith-pro imports dawsmith, is dawsmith-pro a "derivative work" that must also be GPLv3?

**Mitigation**: This is the standard open-core problem. The accepted approach: dawsmith-pro is a separate program that uses dawsmith via its public API (importing it as a library). The CLA grants you a commercial license to dawsmith's code, so you can distribute dawsmith under a commercial license to dawsmith-pro customers. The customer receives both dawsmith (commercial license) and dawsmith-pro (proprietary license), avoiding GPL obligations entirely.

This is exactly how companies like MySQL (GPL + commercial), Qt (LGPL + commercial), and MongoDB (SSPL + commercial) operate.

**Action**: Legal counsel in Phase 1 to structure the CLA and dual license correctly.

### Risk: Community Perceives Pro as Exploitative

**Concern**: "You're taking community contributions and selling them."

**Mitigation**: 
- The open-source product is genuinely valuable on its own, not a crippled demo
- The CLA is transparent about dual-licensing from day one
- The split is logical and defensible (engine vs. intelligence)
- Blog post explaining the business model openly
- Community features are never moved behind the paywall after being open

### Risk: Someone Builds a Competing Pro Layer

**Concern**: Since dawsmith is open source, anyone can build their own templates and evaluation loop.

**Mitigation**: This is a feature, not a bug. If someone builds competing generation logic on top of dawsmith, it validates the platform. Your moat is:
- Speed of iteration (you know the engine best)
- Musical quality of templates (takes domain expertise to build)
- Dataset quality and scale (network effects — more customers → more feedback → better templates)
- Cloud infrastructure (hard to replicate)
- Brand trust and enterprise relationships

If a viable open-source competitor to dawsmith-pro emerges, it means the ecosystem is healthy. Adjust by competing on quality and service, not by restricting the platform.

### Risk: dawsmith Gets Forked and You Lose Control

**Concern**: GPL allows forking. Someone forks dawsmith, removes your branding, and competes.

**Mitigation**: The trademark prevents use of the DAWsmith name. The CLA ensures you retain commercial licensing rights. The fork can exist but can't call itself DAWsmith and won't have the proprietary intelligence layer. Historically, significant forks of open-core products are rare because maintaining a fork is expensive and community loyalty matters.

---

## 11. Key Decisions to Make Before Starting

| Decision | Options | Recommendation |
|---|---|---|
| Legal entity | Sole proprietorship, LLC, C-corp | LLC initially; convert to C-corp if seeking VC |
| CLA type | Apache CLA, Custom CLA | Apache-style ICLA (well-understood, standard) |
| dawsmith-pro distribution | Private PyPI, license-key gated download, hosted only | License-key gated download initially; add private PyPI for enterprise |
| Pricing model | Monthly sub, annual sub, perpetual, usage-based | Monthly + annual sub for Pro; usage-based for cloud API |
| Cloud hosting | AWS, GCP, self-hosted | AWS (most enterprise customers are there) |
| First hire | Second engineer, community manager, sales | Second engineer (C++ binding work is the bottleneck) |
| Tracktion relationship | Cold start, warm outreach, formal partnership | Warm outreach — email their team explaining the project, ask about commercial licensing terms |

---

## 12. Immediate Next Steps

1. **Secure namespaces**: Register `dawsmith` on PyPI, GitHub org, npm (for future WASM), domain dawsmith.com
2. **Legal**: Engage attorney for CLA template, dual-license structure, trademark filing
3. **Tracktion outreach**: Email Tracktion Software explaining the project, discuss commercial licensing for dawsmith-pro's distribution
4. **Proof of concept**: Build minimal nanobind wrapper (Phase 1, Week 1-2 milestone), publish to public GitHub
5. **Community signal**: Post POC on Hacker News, r/python, JUCE forums, KVR
6. **Design partners**: Identify 2-3 AI music companies or research labs willing to alpha-test dawsmith-pro
