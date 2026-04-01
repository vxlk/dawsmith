# DAWsmith Development Plan

## Current State (as of 2026-03-31)

**What works today:**
- C++ abstract interface (`dawsmith.h`, MIT) + Tracktion Engine backend (GPL)
- nanobind Python bindings: Engine, Edit, Track, MidiClip, Plugin, RenderOptions
- VST3 plugin scanning/loading (Dexed tested), parameter get/set
- MIDI clip creation with note add/clear, beat-based positioning
- Track volume/pan/mute
- Offline rendering to WAV
- Real-time playback (play/stop/position)
- Build system: scikit-build-core + CMake, fetches Tracktion Engine v3.2.0
- Built and working on Windows (Python 3.13, x64)
- 2 examples (hello_synth.py, realtime_play.py), 3 test files

**Known issues:**
- Segfault on exit if Python GC destroys edit/engine in wrong order
- Windows-only build (no Linux/macOS CI)
- No built-in plugins (requires external VST3)
- No audio clips, automation, stem export, or batch rendering
- No export formats, validation suite, or metadata output

---

## Phase 1: Stabilize Core (Target: v0.2)

Fix the foundation before adding features.

### 1.1 Object Lifetime Safety
- [x] Fix segfault on exit: prevent Engine destruction while Edits exist (shared_ptr prevent, or ref-count guard)
- [x] Add Python-side prevent + clean error (`EngineDestroyedError`) for accessing dead objects
- [x] Add prevent for dangling Track/Clip/Plugin references after parent deletion (`ObjectDeletedError`)
- [x] Test: concurrent edits, create/destroy cycles, GC order permutations
- [x]: Investigate a better way to deal with the messagemanager - can we use async promises rather than spinning the loop for a certain number of ms in the tracktion_backend?

### 1.2 Hot Reload / Live Session (replaces Built-in Plugins)
- [ ] See `plan/HOT_RELOAD_PLAN.md` for full design
- [ ] C++ foundation: `Engine::pump()`, looping, `Edit::clear_all_tracks()`, `Track::clear_clips/plugins()`
- [ ] Python `LiveSession` class with file watcher and hot reload
- [ ] `dawsmith.live("script.py")` entry point + CLI
- [ ] REPL support with background pump thread
- [ ] Loop mode for iterative development
- [ ] Built-in plugins deprioritized — free VST3s (Dexed, Vital, Surge XT) are plentiful

### 1.3 Audio Clips
- [ ] `track.insert_audio_clip(name, file_path, start_beat, length_beats)`
- [ ] Clip gain, looping

### 1.4 Automation
- [ ] `track.add_automation_point(param_name, beat, value)`
- [ ] Linear interpolation minimum; curves stretch goal

### 1.5 Stem Export
- [ ] `edit.render(opts)` with `opts.per_track = True` renders individual track WAVs
- [ ] Solo/mute-based approach or Tracktion's built-in track render

### 1.6 Cross-Platform CI
- [ ] GitHub Actions matrix: Ubuntu 22.04, macOS 13 (x64), macOS 14 (ARM), Windows 2022
- [ ] Python 3.10-3.13
- [ ] `pip install .` from source on all platforms
- [ ] Tests run without VST3 plugins (use built-in plugins only)

### 1.7 Core Tests (Layer 0-2)
- [ ] Build/import/lifecycle tests (no segfault suite)
- [ ] Data model tests (tempo, tracks, clips, notes, plugins, volume/pan/mute)
- [ ] Basic render tests (silence check, duration check, sample rate, non-silent with built-in synth)
- [ ] Determinism test (same edit renders identical WAV twice)

---

## Phase 2: Export Layer (Target: v0.3)

Pure Python serializers that consume the C++ data model. Each exporter reads track/clip/note/plugin data from the Edit and writes the target format.

### 2.1 Data Extraction API
- [ ] `edit.get_data() -> EditData` returns a Python dataclass snapshot of the entire edit tree
- [ ] EditData / TrackData / ClipData / NoteData / PluginData / AutomationData dataclasses
- [ ] This is the bridge: C++ engine populates it, Python exporters consume it

### 2.2 MIDI Export
- [ ] `edit.export_midi("output.mid")` via `mido` library
- [ ] One track per audio track, tempo meta-event, correct tick timing
- [ ] Roundtrip test: export -> re-import -> compare notes

### 2.3 DAWproject Export (Primary)
- [ ] `edit.export_dawproject("output.dawproject")`
- [ ] XML in ZIP container per the open DAWproject spec
- [ ] Tracks, clips, MIDI notes, automation, tempo, time signature, volume/pan
- [ ] Schema validation test against DAWproject XSD
- [ ] Roundtrip structural test

### 2.4 REAPER RPP Export
- [ ] `edit.export_rpp("output.rpp")`
- [ ] Plain-text RPP with TRACK blocks, MIDI items, tempo, volume/pan

### 2.5 Metadata Export
- [ ] `edit.export_metadata("output.json")` — full ground-truth JSON
- [ ] Every note, parameter, automation point, tempo, key, structure
- [ ] Optional Parquet output for ML pipelines

### 2.6 Ableton ALS Export (Basic)
- [ ] `edit.export_als("output.als")` — gzip XML
- [ ] Tracks, MIDI clips, notes, tempo, volume/pan
- [ ] No plugin state serialization (documented limitation)

### 2.7 Validation Suite v1
- [ ] `dawsmith.validate(edit, "output.wav")` returns dict of pass/fail metrics
- [ ] Checks: tempo detection, silence, clipping, RMS level, duration match
- [ ] Uses librosa/numpy for analysis (no AI)
- [ ] Key detection (chromagram-based)
- [ ] Spectral centroid, band energy ratios

### 2.8 Export Tests (Layer 3)
- [ ] Per-format: valid structure, correct track count, note data matches, tempo matches
- [ ] Cross-format consistency: all formats agree on track count, tempo, note pitches, duration

---

## Phase 3: Scale + Polish (Target: v0.4 / v1.0)

### 3.1 Batch Runner
- [ ] `dawsmith.batch_render(edits, output_dir, workers=N)` — multiprocessing parallel render
- [ ] Each worker: create engine -> render -> export -> validate -> cleanup

### 3.2 FL Studio FLP Export
- [ ] Via `pyflp` library integration

### 3.3 Performance
- [ ] Benchmark: render time for 30s/4-track/2-plugin arrangement
- [ ] Memory: no leak over 100 create/render/destroy cycles
- [ ] Import time < 2s

### 3.4 Documentation
- [ ] API reference (auto-generated from docstrings)
- [ ] 5+ tutorial examples (MIDI composition, multi-track mix, export all formats, validation, batch render)
- [ ] One example genre template in repo (basic 4-bar drum loop generator)

### 3.5 Packaging
- [ ] Pre-built wheels on PyPI for Windows/macOS/Linux (x64 + ARM macOS)
- [ ] `pip install dawsmith` works without C++ toolchain

### 3.6 Advanced Tests (Layer 4-5)
- [ ] Integration: template -> render -> validate -> export -> verify
- [ ] E2E: full pipeline end-to-end
- [ ] Scale (nightly): 100 renders all pass, memory stable
- [ ] Golden file regression tests

---

## Phase 4: dawsmith-pro (Private, Post-v1.0)

Separate private repo. Imports `dawsmith` as a dependency.

### Intelligence Layer
- [ ] Specification system (Spec class: genre, BPM range, key, duration, tracks)
- [ ] Genre templates (5 initial: doom metal, pop, electronic, hip hop, ambient)
- [ ] Evaluation loop (render -> validate -> fix -> re-render)
- [ ] Reference audio analysis (extract tempo/key/spectral profile)
- [ ] Constraint solver (notes in key, valid ranges, coherent structure)

### Scale
- [ ] Dataset generation orchestrator (spec -> N variations -> validated output)
- [ ] Agent integration (LLM tool-use interface for Claude/GPT)
- [ ] Quality scoring (multi-metric, beyond pass/fail)
- [ ] Cloud API (REST server for hosted rendering)
- [ ] 30+ genre templates

---

## Architecture

```
dawsmith-pro (Proprietary, Python)
    |
    |  imports dawsmith
    v
dawsmith (GPLv3, Python + C++)
    |
    +-- Python layer: validate.py, export/, batch.py
    |       consumes EditData dataclasses
    |
    +-- nanobind bindings (_native.pyd/.so)
    |       wraps dawsmith.h interface
    |
    +-- dawsmith.h (MIT, C++ abstract interface)
    |
    +-- tracktion_backend (GPL, C++ implementation)
            |
            v
        Tracktion Engine v3.2.0 + JUCE (C++)
```

**License boundary:** dawsmith.h is MIT so proprietary backends can link against it. The Python package and Tracktion backend are GPL. dawsmith-pro is proprietary (customers receive dawsmith under commercial license via CLA).

---

## Priority Order

1. **Fix segfault** (object lifetime) -- blocks everything
2. **Hot reload / live session** -- differentiator feature (see `plan/HOT_RELOAD_PLAN.md`)
3. **Cross-platform CI** -- confidence in every change
4. **Audio clips + automation** -- completes the core data model
5. **EditData extraction** -- bridges C++ to Python export layer
6. **MIDI export** -- simplest format, proves the export pipeline
7. **Validation suite** -- proves renders are correct
8. **DAWproject export** -- primary format target
9. **Remaining exports** (RPP, ALS, metadata)
10. **Stem export + batch runner** -- scale features
11. **PyPI wheels** -- adoption
12. **dawsmith-pro** -- revenue
