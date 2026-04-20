# DAWproject Export/Import Implementation Plan

## Context

dawsmith needs a .dawproject export/import to become the primary interchange format (Phase 2, Section 2.3 of DEVELOPMENT_PLAN.md). The C++ engine is write-only (no getters for tracks/clips/notes), so we need a Python-side shadow model to track state. The user has decided to:
- Use `dawproject-py` (MIT) as a dependency for XML/ZIP serialization
- Adopt dawproject conventions as primary (pan 0.0-1.0 normalized, velocity 0.0-1.0)
- Embed audio files in the ZIP
- Require roundtrip tests (export → parse → reconstruct engine objects → compare)

---

## Step 1: `src/dawsmith/edit_data.py` — EditData dataclasses

Pure Python dataclasses using dawproject conventions. No dependencies.

```python
@dataclass NoteData:     pitch (int 0-127), start_beat, length_beats, velocity (float 0.0-1.0), channel (int)
@dataclass MidiClipData: name, start_beat, length_beats, notes: list[NoteData]
@dataclass AudioClipData: name, file_path, start_beat, length_beats, gain (linear), loop (bool)
@dataclass TrackData:    name, volume (linear), pan (0.0-1.0 normalized), mute, midi_clips, audio_clips
@dataclass EditData:     tempo, time_sig_numerator, time_sig_denominator, tracks, app_name, app_version
```

**Test file:** `tests/test_edit_data.py` — defaults, equality, construction

---

## Step 2: Add `dawproject-py` dependency

**Modify:** `pyproject.toml`
```toml
dependencies = [
    "dawproject @ git+https://github.com/roex-audio/dawproject-py.git",
]
```

`lxml>=5.0` is a transitive dep of dawproject-py (no need to list separately).

---

## Step 3: `src/dawsmith/dawproject_io.py` — Export function

```python
def export_dawproject(edit_data: EditData, output_path: str | Path) -> None:
```

Algorithm:
1. `Referenceable.reset_id()`
2. Create `Project` + `Application("DAWsmith", version)`
3. Create `Transport` with tempo (`RealParameter`, `unit=BPM`) and time sig
4. Create master `Track`/`Channel` (role=MASTER)
5. For each `TrackData`: create Track + Channel (volume LINEAR, pan NORMALIZED, mute), route to master
6. For each `MidiClipData`: create `Clip` > `Notes` > `Note` objects (key=pitch, vel=velocity as-is since already 0.0-1.0)
7. For each `AudioClipData`: create `Clip` > `Audio` with `FileReference`, read file bytes into embedded_files dict
8. Build `Arrangement` > `Lanes` (timeUnit=BEATS) > per-track `Lanes` > `Clips`
9. `DawProject.validate(project)` — XSD check before writing
10. `DawProject.save(project, metadata, embedded_files, output_path)`

**Test:** `tests/test_dawproject_io.py::TestExport` — file creation, valid ZIP, contains project.xml/metadata.xml, XSD validation, audio embedding

---

## Step 4: Import function

```python
def import_dawproject(file_path: str | Path, *, audio_dir: str | Path | None = None) -> EditData:
```

Algorithm:
1. `DawProject.load_project()` + `DawProject.load_metadata()`
2. Extract tempo, time sig from Transport
3. Walk `project.structure` for Track objects → TrackData (volume, pan, mute from Channel)
4. Walk arrangement lanes for Clips → MidiClipData/AudioClipData
5. Extract embedded audio to `audio_dir` (or tempdir)
6. Return populated `EditData`

**Test:** `tests/test_dawproject_io.py::TestImport` — tempo, tracks, notes, volume/pan/mute readback

---

## Step 5: Roundtrip tests

```python
def reconstruct_edit(engine: Engine, edit_data: EditData) -> Edit:
```

Calls existing write API: `create_edit()`, `insert_audio_track()`, `set_volume/pan/mute()`, `insert_midi_clip()`, `add_note()`, `insert_audio_clip()`, `set_gain/loop()`.

Needs convention translation at this boundary:
- `pan`: `(edit_data_pan * 2.0) - 1.0` → engine's -1.0..+1.0 range
- `velocity`: `round(vel * 127)` → engine's 0-127 int

**Tests:** `tests/test_dawproject_io.py::TestRoundtrip`
- Empty edit roundtrip
- MIDI notes survive export→import (pitch, timing, velocity)
- Multi-track with different volume/pan/mute
- Audio clips (gain, loop, position)
- Full engine roundtrip: EditData → export → import → reconstruct → compare shadow data

---

## Step 6: Shadow model wrappers in `__init__.py`

Wrap native objects with `Smart*` classes that delegate to C++ while maintaining `EditData` shadow state. This is the most invasive change.

**Key classes:**
- `SmartEngine` — wraps `Engine`, `create_edit()` returns `SmartEdit`
- `SmartEdit` — wraps `Edit`, holds `EditData`, `insert_audio_track()` returns `SmartTrack`
- `SmartTrack` — wraps `Track`, holds `TrackData`, volume/pan/mute update shadow
- `SmartMidiClip` — wraps `MidiClip`, holds `MidiClipData`, `add_note()` records to shadow
- `SmartAudioClip` — wraps `AudioClip`, holds `AudioClipData`

**Convention translation in wrappers (dawproject convention in, engine convention out):**

| Public API (dawproject) | Engine call | Translation |
|---|---|---|
| `set_pan(0.75)` (normalized) | `native.set_pan(0.5)` | `(pan * 2) - 1` |
| `add_note(vel=0.787)` (normalized) | `native.add_note(vel=100)` | `round(vel * 127)` |
| `set_volume(0.5)` (linear) | `native.set_volume(0.5)` | none |

**Property access:** Each wrapper exposes `.data` for the shadow dataclass and `._native` for escape-hatch access.

**Convenience:** `SmartEdit.export_dawproject(path)` as a shortcut for `export_dawproject(self.data, path)`.

**Test:** `tests/test_shadow_model.py` — wrappers correctly track all mutations

---

## Step 7: Update existing tests

The pan/velocity convention change affects:
- `tests/test_edit.py:89`: `track.set_pan(-0.3)` → `track.set_pan(0.35)` (normalized)
- `tests/test_edit.py:42`: `velocity=100` → `velocity=0.787` (normalized)
- `tests/test_lifetime.py:60`: `track.set_pan(-0.2)` → `track.set_pan(0.4)`
- All `velocity=80`, `velocity=90`, `velocity=100` in lifetime tests → normalized equivalents

**Backward compat option:** Accept both conventions with auto-detect (values > 1.0 treated as legacy MIDI int, with deprecation warning). This preserves existing code while migrating.

---

## Files Summary

| File | Action | Purpose |
|---|---|---|
| `src/dawsmith/edit_data.py` | **NEW** | EditData dataclass hierarchy |
| `src/dawsmith/dawproject_io.py` | **NEW** | export/import/reconstruct functions |
| `tests/test_edit_data.py` | **NEW** | Dataclass unit tests |
| `tests/test_dawproject_io.py` | **NEW** | Export, import, roundtrip, XSD tests |
| `tests/test_shadow_model.py` | **NEW** | Shadow model tracking tests |
| `src/dawsmith/__init__.py` | **MODIFY** | Smart wrapper classes, convention translation, new exports |
| `pyproject.toml` | **MODIFY** | Add dawproject-py dependency |
| `tests/conftest.py` | **MODIFY** | Add sine_wav fixture, EditData helpers |
| `tests/test_edit.py` | **MODIFY** | Update pan/velocity to dawproject conventions |
| `tests/test_lifetime.py` | **MODIFY** | Update pan/velocity to dawproject conventions |

---

## Implementation Order (test-first)

1. **edit_data.py + test_edit_data.py** — pure Python, no deps, instant feedback
2. **pyproject.toml** — add dawproject-py dep, verify install
3. **dawproject_io.py export + TestExport** — serialize EditData → .dawproject, XSD validation
4. **dawproject_io.py import + TestImport** — parse .dawproject → EditData
5. **TestRoundtrip (data only)** — export → import → compare EditData equality
6. **__init__.py Smart wrappers + test_shadow_model.py** — shadow model tracking
7. **reconstruct_edit + engine roundtrip test** — full engine roundtrip
8. **Update existing tests** — pan/velocity convention migration
9. **Update __all__ and public API** — expose new functions

---

## Verification

1. `pytest tests/test_edit_data.py` — dataclass correctness
2. `pytest tests/test_dawproject_io.py` — export creates valid ZIP, XSD passes, import reads back correctly, roundtrip preserves all fields
3. `pytest tests/test_shadow_model.py` — wrappers track all mutations
4. `pytest` (full suite) — no regressions in existing tests
5. Manual: open exported .dawproject in Bitwig/Studio One/Reaper to verify real DAW compatibility (stretch goal)
