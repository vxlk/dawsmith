# Code-First DAW: Automated Testing Plan

## Purpose

This document defines the testing strategy for incrementally proving correctness as the code-first DAW is developed. The system has an unusual testing surface — it spans C++ bindings, audio rendering, musical correctness, spectral analysis, and cross-DAW file format serialization. Traditional unit/integration/e2e categories still apply, but the domain-specific testing is where the real complexity lives.

Every test in this plan should be automated, run in CI, and produce a clear pass/fail signal. No human listening required for the automated suite.

---

## 1. Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E ╲          Full pipeline tests
                 ╱ (slow) ╲        Generate → Render → Validate → Export → Verify
                ╱──────────╲
               ╱  Integration╲     Multi-component tests
              ╱   (medium)    ╲    Engine + bindings + render + analysis
             ╱────────────────╲
            ╱   Audio Domain    ╲   Render correctness, spectral validation,
           ╱    (medium-fast)    ╲  musical analysis, format verification
          ╱──────────────────────╲
         ╱      Unit Tests        ╲  Data model, serializers, validators,
        ╱       (fast)             ╲ MIR utilities, template logic
       ╱────────────────────────────╲
      ╱      Build & Binding Tests    ╲  Compilation, import, lifecycle,
     ╱         (fast)                  ╲ memory safety, platform checks
    ╱────────────────────────────────────╲
```

---

## 2. Layer 0: Build & Binding Tests

These run first in CI. If these fail, nothing else matters.

### 2.1 Compilation Tests

```yaml
test_matrix:
  os: [ubuntu-22.04, macos-13, macos-14-arm64, windows-2022]
  python: ["3.10", "3.11", "3.12", "3.13"]
```

| Test | What It Proves | When Added |
|---|---|---|
| `test_builds_cleanly` | C++ compiles with no warnings on all platforms | Day 1 |
| `test_wheel_installs` | `pip install` works from built wheel | Day 1 |
| `test_import_succeeds` | `import tracktion as te` doesn't crash or segfault | Day 1 |
| `test_no_llvm_conflict` | Import after `import jax` and `import torch` doesn't segfault | Day 1 |
| `test_import_order_irrelevant` | Import before and after common ML libraries both work | Day 1 |

### 2.2 Engine Lifecycle Tests

| Test | What It Proves | When Added |
|---|---|---|
| `test_engine_create_destroy` | Engine can be created and garbage collected cleanly | Day 1 |
| `test_engine_create_multiple` | Multiple Engine instances don't conflict | Day 1 |
| `test_edit_create_destroy` | Edit can be created and garbage collected | Day 1 |
| `test_edit_survives_engine_gc` | Edit holds reference to Engine; no dangling pointer | Week 1 |
| `test_track_survives_edit_gc` | Child object lifetime management works | Week 1 |
| `test_no_memory_leaks` | Repeated create/destroy cycles don't leak (check RSS growth) | Week 2 |
| `test_message_manager_headless` | JUCE MessageManager initializes without a GUI event loop | Day 1 |
| `test_concurrent_edits` | Multiple Edits in same Engine work independently | Week 2 |

### 2.3 Platform-Specific Tests

| Test | What It Proves | When Added |
|---|---|---|
| `test_audio_device_enumeration` | Engine can list audio devices (even if none present in CI) | Phase 1 |
| `test_plugin_scan_paths` | Plugin scan doesn't crash when scan paths are empty | Phase 1 |
| `test_temp_directory_cleanup` | Renders don't leave temp files behind | Phase 1 |

---

## 3. Layer 1: Unit Tests (Data Model)

Pure Python tests of the data model, serializers, validators, and utilities. No audio rendering. Fast — should run in <10 seconds total.

### 3.1 Data Model Construction

| Test | What It Proves |
|---|---|
| `test_edit_has_tempo` | Edit.tempo_sequence exists and defaults to 120 BPM |
| `test_set_bpm` | Setting BPM to 65 reads back as 65 |
| `test_insert_audio_track` | Track appears in edit.tracks, has correct name |
| `test_insert_midi_clip` | Clip appears on track, has correct start/length |
| `test_add_midi_note` | Note appears in clip with correct pitch/velocity/timing |
| `test_midi_note_bounds` | Notes outside 0-127 pitch range raise ValueError |
| `test_clip_position_beats` | Clip at beat 8 with length 4 has correct end position |
| `test_automation_add_point` | Automation point appears with correct time/value |
| `test_automation_curve_type` | Linear vs. curved interpolation setting persists |
| `test_track_volume_pan` | Volume and pan values persist and read back correctly |
| `test_track_solo_mute` | Solo/mute state persists |
| `test_nested_folder_tracks` | Folder tracks can contain child tracks |
| `test_multiple_clips_same_track` | Multiple clips on one track don't interfere |
| `test_overlapping_clips` | Overlapping clips handled or rejected correctly |
| `test_tempo_change_midway` | Tempo sequence with multiple points stores correctly |
| `test_time_signature_change` | Time signature changes at specific beats |
| `test_edit_duration` | Edit reports correct duration based on last clip end |

### 3.2 Plugin Interface

| Test | What It Proves |
|---|---|
| `test_insert_builtin_plugin` | Built-in reverb/compressor/EQ can be instantiated |
| `test_get_parameter_list` | Plugin reports its parameter names and ranges |
| `test_set_parameter_value` | Setting parameter value reads back correctly |
| `test_parameter_out_of_range` | Values outside declared range are clamped or rejected |
| `test_plugin_chain_order` | Multiple plugins on a track maintain insertion order |
| `test_remove_plugin` | Removing a plugin from chain works cleanly |

### 3.3 Validation Suite Unit Tests

Test the validators themselves against known-good and known-bad audio fixtures.

| Test | What It Proves |
|---|---|
| `test_tempo_detector_120bpm` | Detects 120 BPM from a known 120 BPM click track |
| `test_tempo_detector_65bpm` | Detects 65 BPM from a known 65 BPM click track |
| `test_key_detector_c_major` | Detects C major from a known C major scale |
| `test_key_detector_d_minor` | Detects D minor from a known D minor arpeggio |
| `test_silence_detector` | Correctly identifies a silent audio buffer |
| `test_clipping_detector` | Correctly identifies a buffer with samples at ±1.0 |
| `test_spectral_centroid` | Computes expected centroid for a known sine wave |
| `test_band_energy_ratio` | Computes expected band ratios for pink noise |
| `test_rms_level` | Computes correct RMS for a known-amplitude sine wave |
| `test_onset_detection` | Detects onsets at correct positions in a click track |

**Fixtures**: A set of short WAV files (1-5 seconds each) with known properties, committed to the repo. Generated once by a script, then frozen as test fixtures.

```
tests/fixtures/audio/
├── click_120bpm_4bars.wav
├── click_65bpm_4bars.wav
├── sine_440hz_1sec.wav
├── sine_100hz_1sec.wav
├── c_major_scale.wav
├── d_minor_arpeggio.wav
├── silence_1sec.wav
├── clipped_sine.wav
├── pink_noise_1sec.wav
└── drum_loop_120bpm.wav
```

### 3.4 Template Unit Tests

Test genre templates produce valid data model objects without rendering.

| Test | What It Proves |
|---|---|
| `test_doom_metal_template_creates_edit` | Template returns a valid Edit object |
| `test_doom_metal_template_has_tracks` | Edit has expected tracks (drums, guitar, bass) |
| `test_doom_metal_template_bpm_range` | BPM is within 55-80 range |
| `test_doom_metal_template_key` | Key is a valid musical key |
| `test_doom_metal_template_duration` | Duration is within specified range |
| `test_doom_metal_template_midi_in_key` | All MIDI notes are within the specified key/scale |
| `test_doom_metal_template_note_ranges` | Notes are within playable range for each instrument |
| `test_template_randomization` | Two calls with different seeds produce different arrangements |
| `test_template_deterministic` | Two calls with same seed produce identical arrangements |

---

## 4. Layer 2: Audio Domain Tests (Render Correctness)

These tests render audio and validate the output. Each test renders a short clip (1-4 seconds) and analyzes the result.

### 4.1 Basic Render Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_render_silence` | Empty edit renders silent audio of correct duration | RMS < -80 dB |
| `test_render_not_empty` | Edit with content produces non-silent audio | RMS > -60 dB |
| `test_render_correct_duration` | 4-beat render at 120 BPM produces exactly 2 seconds | Sample count = 88200 |
| `test_render_correct_sample_rate` | Output is 44100 Hz when engine is set to 44100 | WAV header check |
| `test_render_correct_channels` | Stereo render produces 2-channel audio | Shape check |
| `test_render_bit_depth_24` | 24-bit render produces valid 24-bit WAV | WAV header check |
| `test_render_no_clipping` | Default render doesn't clip | Peak < 1.0 |

### 4.2 MIDI Rendering Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_midi_note_produces_audio` | Single MIDI note through built-in synth produces sound | RMS > -60 dB during note, silence after |
| `test_midi_note_correct_pitch` | MIDI note 69 (A4) produces fundamental at ~440 Hz | Spectral peak at 440 Hz ± 5 Hz |
| `test_midi_note_correct_timing` | Note at beat 2 starts at the right sample offset | Onset detection matches expected position |
| `test_midi_velocity_affects_volume` | Velocity 127 is louder than velocity 40 | RMS comparison |
| `test_midi_multiple_notes` | Chord (3 notes) produces more complex spectrum | Spectral peak count |
| `test_midi_note_off` | Note-off stops the sound | RMS drops below threshold after note end |

### 4.3 Audio Clip Rendering Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_audio_clip_plays` | Audio clip produces output matching source | Cross-correlation > 0.95 |
| `test_audio_clip_position` | Clip at beat 4 starts at correct sample offset | Onset detection |
| `test_audio_clip_loop` | Looped clip repeats correctly | Cross-correlation of loop segments |
| `test_audio_clip_gain` | Clip gain of -6 dB reduces level by ~half | RMS ratio within 0.5 ± 0.05 |
| `test_audio_clip_time_stretch` | Stretched clip maintains pitch | Spectral centroid unchanged ± 10% |

### 4.4 Mixing Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_two_tracks_sum` | Two tracks render louder than either alone | RMS of mix > RMS of each solo |
| `test_track_mute` | Muted track produces silence in its stem | Stem RMS < -80 dB |
| `test_track_solo` | Solo'd track is only audible source | Mix matches solo'd track's stem |
| `test_track_volume` | Volume at -6 dB reduces stem by ~6 dB | RMS ratio |
| `test_track_pan_left` | Left-panned track: energy only in left channel | Right channel RMS < -60 dB |
| `test_track_pan_right` | Right-panned track: energy only in right channel | Left channel RMS < -60 dB |
| `test_stem_export` | Per-track stems sum to approximately the full mix | Cross-correlation > 0.9 |

### 4.5 Automation Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_volume_automation_ramp` | Linear ramp from -inf to 0 dB over 4 beats | RMS increases monotonically across segments |
| `test_parameter_automation` | Filter cutoff automation changes spectral content | Spectral centroid increases over time |
| `test_tempo_automation` | Tempo change at beat 8 doubles beat spacing in second half | Onset spacing analysis |

### 4.6 Plugin Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_builtin_reverb` | Reverb extends signal beyond note-off | Energy persists after source ends |
| `test_builtin_compressor` | Compressor reduces dynamic range | Peak-to-RMS ratio decreases |
| `test_builtin_eq_lowpass` | Low-pass at 1kHz removes high frequencies | Energy above 2kHz reduced >12 dB |
| `test_builtin_eq_highpass` | High-pass at 500Hz removes low frequencies | Energy below 250Hz reduced >12 dB |
| `test_plugin_bypass` | Bypassed plugin produces identical output | Cross-correlation > 0.999 |
| `test_vst3_load` | Known open-source VST3 loads without crash | Parameter count > 0 |
| `test_vst3_render` | VST3 instrument produces audio from MIDI | RMS > -60 dB |

**VST3 fixture plugins** (open-source, cross-platform):

```
tests/fixtures/plugins/
├── surge-xt.vst3/
└── dragonfly-reverb.vst3/
```

Use built-in plugins for most tests; reserve VST3 tests for nightly runs.

### 4.7 Determinism Tests

| Test | What It Proves | How Verified |
|---|---|---|
| `test_render_deterministic` | Same Edit rendered twice → identical output | Byte-level WAV comparison |
| `test_render_deterministic_across_runs` | Same script in separate processes → identical output | Byte-level comparison |
| `test_seed_determinism` | Template with same seed → identical Edit and audio | Data model + render comparison |

---

## 5. Layer 3: Export Format Tests

### 5.1 DAWproject Export (Primary Target)

| Test | What It Proves | How Verified |
|---|---|---|
| `test_dawproject_valid_zip` | Output is a valid ZIP container | `zipfile.is_zipfile()` |
| `test_dawproject_has_project_xml` | Container includes `project.xml` | Zip contents check |
| `test_dawproject_valid_xml` | Well-formed XML | XML parser succeeds |
| `test_dawproject_schema_valid` | Validates against DAWproject XSD | Schema validation |
| `test_dawproject_tempo_correct` | Tempo value matches source Edit | Parse and compare |
| `test_dawproject_track_count` | Correct number of Track elements | XPath count |
| `test_dawproject_track_names` | Track names match source | Parse and compare |
| `test_dawproject_note_data` | Note pitch/time/duration/velocity match source | Full note comparison |
| `test_dawproject_automation_values` | Automation point times/values match source | Point-by-point comparison |
| `test_dawproject_audio_refs` | Referenced audio files exist in container | Zip contents check |
| `test_dawproject_plugin_refs` | Plugin deviceID/deviceName correct | Parse and compare |
| `test_dawproject_volume_pan` | Channel volume/pan match source | Parse and compare |
| `test_dawproject_roundtrip` | Export → re-import produces equivalent data model | Field-by-field comparison |

### 5.2 REAPER RPP Export

| Test | What It Proves | How Verified |
|---|---|---|
| `test_rpp_parseable` | Syntactically valid RPP | Balanced delimiters check |
| `test_rpp_track_count` | Correct TRACK block count | Parse and count |
| `test_rpp_track_names` | Names match source | Parse NAME fields |
| `test_rpp_tempo_correct` | TEMPO field matches source BPM | Parse and compare |
| `test_rpp_midi_notes` | MIDI events contain correct note data | Parse event bytes |
| `test_rpp_volume_pan` | VOLPAN fields match source | Parse and compare |

### 5.3 Ableton ALS Export

| Test | What It Proves | How Verified |
|---|---|---|
| `test_als_valid_gzip` | Valid gzip file | `gzip.open()` succeeds |
| `test_als_valid_xml` | Decompressed content is well-formed XML | XML parser succeeds |
| `test_als_track_count` | Correct number of track elements | XPath count |
| `test_als_track_names` | Track names match source | Parse and compare |
| `test_als_tempo` | Tempo value matches source | Parse and compare |
| `test_als_midi_notes` | MIDI note data present with correct values | Parse note elements |

### 5.4 MIDI Export

| Test | What It Proves | How Verified |
|---|---|---|
| `test_midi_valid_file` | Valid Standard MIDI File | `mido.MidiFile()` opens |
| `test_midi_track_count` | Correct track count | Compare |
| `test_midi_tempo` | Tempo meta-event matches BPM | Parse tempo event |
| `test_midi_note_count` | Total notes match source | Count note_on events |
| `test_midi_note_pitches` | All pitches match source | Compare sorted lists |
| `test_midi_note_timing` | Note-on times within 1 tick of expected | Tick comparison |

### 5.5 Metadata Export

| Test | What It Proves | How Verified |
|---|---|---|
| `test_metadata_valid_json` | Valid JSON | `json.loads()` succeeds |
| `test_metadata_tracks_present` | Track metadata for each track | Key check |
| `test_metadata_note_count` | Matches actual MIDI data | Cross-reference with Edit |
| `test_metadata_param_values` | Plugin parameter snapshots match Edit | Cross-reference |
| `test_metadata_structure` | Song structure labels and positions present | Key/value check |
| `test_metadata_tempo_key` | Tempo and key match Edit | Value comparison |
| `test_metadata_parquet` | Parquet loads with correct schema | `pandas.read_parquet()` |

### 5.6 Cross-Format Consistency

The most important export tests — all formats must agree on the music.

| Test | What It Proves |
|---|---|
| `test_all_formats_same_track_count` | DAWproject, RPP, ALS, MIDI all have same track count |
| `test_all_formats_same_tempo` | All formats encode the same BPM |
| `test_all_formats_same_note_count` | All formats have same total MIDI note count |
| `test_all_formats_same_note_pitches` | All formats have identical sorted pitch lists |
| `test_all_formats_same_duration` | All formats represent same arrangement duration |
| `test_metadata_matches_render` | Metadata timing matches audio analysis of rendered WAV |

---

## 6. Layer 4: Integration Tests

### 6.1 Template → Render → Validate

One test per genre template. Each renders 8-16 bars and validates.

| Test | Validates |
|---|---|
| `test_doom_metal_renders_valid` | Non-silent, non-clipping, correct tempo/key, spectral centroid < 2kHz, bass energy > 30% |
| `test_pop_renders_valid` | Correct tempo (100-130 BPM), balanced spectrum |
| `test_electronic_renders_valid` | Correct tempo (120-140 BPM), kick presence |
| `test_jazz_renders_valid` | Correct tempo, key, instrument presence |
| (one per template) | Genre-appropriate spectral and structural metrics |

### 6.2 Template → Export → Roundtrip

| Test | What It Proves |
|---|---|
| `test_doom_metal_dawproject_roundtrip` | Export and re-import preserves all data |
| `test_doom_metal_midi_roundtrip` | MIDI export and re-import recovers all notes |

### 6.3 Batch Generation

| Test | What It Proves | Runtime |
|---|---|---|
| `test_batch_10_all_valid` | 10 randomized renders all pass validation | <2 min |
| `test_batch_10_all_unique` | Different seeds → different audio | Hash comparison |
| `test_batch_metadata_complete` | All 10 produce complete metadata | Schema check |
| `test_batch_parallel_matches_sequential` | Parallel runner matches sequential output | Comparison |

---

## 7. Layer 5: End-to-End Pipeline Tests

Full pipeline tests. Run on merge to main.

### 7.1 Full Generation Pipeline

| Test | What It Proves |
|---|---|
| `test_e2e_doom_metal` | Spec → template → render → validate → export (all formats) → metadata. All outputs exist and pass. |
| `test_e2e_pop` | Same for pop. |
| `test_e2e_electronic` | Same for electronic. |
| `test_e2e_custom_spec` | Custom user spec produces valid outputs. |

### 7.2 Agent Simulation

Scripted mock agent — no LLM, just predictable modifications.

| Test | What It Proves |
|---|---|
| `test_agent_corrects_tempo` | Wrong tempo → validation catches → fix → pass |
| `test_agent_corrects_key` | Wrong key → validation catches → fix → pass |
| `test_agent_corrects_silence` | Silent track → validation catches → fix → pass |
| `test_agent_converges` | 5 iterations, each closer to spec (monotonic improvement) |
| `test_agent_terminates` | Max iterations reached → exits gracefully |

### 7.3 Scale Tests (Nightly Only)

| Test | What It Proves | Runtime |
|---|---|---|
| `test_scale_100_renders` | 100 randomized renders all pass | ~15 min |
| `test_scale_100_exports` | 100 renders export to all formats | ~20 min |
| `test_scale_memory_stable` | RSS doesn't grow >2x over 100 renders | ~15 min |
| `test_scale_output_size` | Average output < 50MB per track | File size check |

---

## 8. Regression Infrastructure

### 8.1 Golden File Tests

Reference WAVs for critical renders. Byte-identical comparison.

```
tests/golden/renders/
├── simple_midi_chord.wav
├── two_track_mix.wav
├── automation_ramp.wav
└── builtin_reverb_tail.wav
```

Failing golden test = regression or intentional change requiring explicit golden file update with commit message.

### 8.2 Export Snapshot Tests

Reference DAWproject XML, RPP, ALS, MIDI files for structural comparison.

```
tests/golden/exports/
├── simple_project.dawproject
├── simple_project.rpp
├── simple_project.als
├── simple_project.mid
└── simple_project.metadata.json
```

### 8.3 Performance Benchmarks (Nightly)

| Metric | Baseline Target | Alert if Exceeds |
|---|---|---|
| Render: 30s stereo, 4 tracks, 2 plugins | < 5 seconds | > 10 seconds |
| Import: `import tracktion` | < 2 seconds | > 5 seconds |
| Memory: 16 tracks, 64 clips | < 200 MB RSS | > 500 MB |
| DAWproject export | < 500 ms | > 2 seconds |
| Validation suite: 30s WAV | < 1 second | > 3 seconds |

Results stored as time series. Alert on >2x regression.

---

## 9. CI/CD Pipeline

### On Every Push / PR (~15 min total)

```
Stage 1: Build ──► Stage 2: Unit Tests ──► Stage 3: Audio Domain ──► Stage 4: Export ──► Stage 5: Integration
 (5 min)            (30 sec)                (3 min)                   (1 min)            (5 min)
```

### On Merge to Main (add ~10 min)

```
+ Stage 6: E2E Pipeline Tests + Agent Simulation
```

### Nightly (add ~30 min)

```
+ Stage 7: Scale Tests + Performance Benchmarks
```

### On Release Tag (add ~30 min)

```
+ Stage 8: Full suite on all OS/Python matrix + Wheel build/install verification
```

---

## 10. Test Fixture Management

### Committed to Repo (~60 MB)

```
tests/fixtures/
├── audio/           # Short WAVs with known properties (~5 MB)
├── plugins/         # Open-source VST3 binaries (~50 MB) — or downloaded in CI
├── midi/            # Reference MIDI files
├── golden/          # Golden reference WAVs and export files
└── specs/           # Test specification JSONs
```

### Generated During CI (gitignored)

```
tests/output/
├── renders/         # WAV files from current run
├── exports/         # Project files from current run
├── metadata/        # JSON/Parquet from current run
└── benchmarks/      # Performance measurements
```

### VST3 Plugin Strategy

- **Most tests**: Use Tracktion Engine built-in plugins only (no external dependencies)
- **Nightly**: Download pre-built open-source VST3s (Surge XT, Dragonfly Reverb) from GitHub Releases
- **Never**: Depend on commercial plugins in CI

---

## 11. Milestone Acceptance Criteria

### Phase 1 Complete When:

- [ ] All Layer 0 (build/binding) tests pass on Linux + macOS + Windows
- [ ] All data model unit tests pass
- [ ] Basic render tests pass (silence, duration, sample rate, channels)
- [ ] MIDI render tests pass (correct pitch, timing, velocity)
- [ ] Mixing tests pass (volume, pan, mute, solo, stems)
- [ ] Automation ramp test passes
- [ ] Built-in plugin tests pass (reverb, compressor, EQ)
- [ ] Determinism tests pass
- [ ] At least 4 golden file tests established and passing
- [ ] Validation suite correctly rejects silence, clipping, wrong tempo, wrong key

### Phase 2 Complete When:

- [ ] DAWproject export passes schema validation and roundtrip test
- [ ] RPP export structural tests pass
- [ ] MIDI roundtrip test passes
- [ ] Cross-format consistency tests pass
- [ ] 3+ genre template integration tests pass
- [ ] All metadata export tests pass
- [ ] Export snapshot tests established and passing

### Phase 3 Complete When:

- [ ] Batch 100-render test passes
- [ ] Memory stability test passes
- [ ] Performance benchmarks established with alerts
- [ ] Agent simulation tests pass
- [ ] ALS export basic tests pass
- [ ] 10+ genre template integration tests pass
- [ ] Full E2E pipeline tests pass for all genres

---

## 12. Testing Philosophy

1. **No human listening.** Every audio assertion is backed by a metric — RMS, spectral centroid, cross-correlation, onset detection, band energy. If you can't measure it, you can't test it.

2. **Determinism is sacred.** Same input → same output. Flaky tests mean bugs in the system, not in the tests.

3. **Test the contract, not the implementation.** "MIDI 69 produces 440 Hz" — not "internal buffer index 37 equals 0.5." Engine upgrades shouldn't break tests.

4. **Golden files are insurance, not truth.** They catch unintended changes. Intentional changes update goldens with an explanatory commit.

5. **Export tests verify structure, not rendering.** We check that DAWproject XML has the right tracks and notes — not that Bitwig renders it identically to us.

6. **Cross-format consistency is the highest-value test.** If all formats agree on the music, the system is correct.

7. **Scale tests are separate from correctness tests.** Correctness runs in <15 minutes. Scale runs nightly.
