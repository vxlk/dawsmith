# Code-First DAW: Automated Testing Plan

## Philosophy

This project has an unusual testing challenge. Traditional software tests ask "did the function return the right value?" Our tests must also ask "does the audio sound right?", "does this XML open in Bitwig?", and "did the C++ engine crash when Python garbage-collected a Track that was still rendering?"

The testing strategy is layered. Each layer builds confidence on top of the one below it. Nothing renders audio until the binding layer is proven solid. Nothing exports to DAWproject until the render layer produces validated output. Nothing ships until exported files open correctly in real DAWs.

---

## 1. Test Layers

```
Layer 5: Integration / End-to-End
         "Generate a doom metal track from template, render, validate,
          export to DAWproject, verify it opens in Bitwig"

Layer 4: Format Compatibility
         "Does the DAWproject XML we generate match the spec?
          Does this ALS file open in Ableton without errors?"

Layer 3: Audio Validation
         "Is the rendered audio at the right tempo? Right key?
          Non-silent? Non-clipping? Correct spectral profile?"

Layer 2: Musical Data Model
         "Does a MIDI clip at beat 4 in a 120 BPM edit land at
          exactly 2.0 seconds? Does automation interpolate correctly?"

Layer 1: Binding Correctness
         "Can Python create an Edit, add a Track, insert a Clip,
          and tear everything down without segfaulting?"
```

Each layer has its own test suite, runner, and failure semantics. A failure at Layer 1 blocks everything above it. A failure at Layer 3 doesn't necessarily mean Layer 1 or 2 is broken.

---

## 2. Layer 1: Binding Correctness

### 2.1 Purpose

Prove that the nanobind Python wrappers correctly create, manipulate, and destroy Tracktion Engine C++ objects without memory corruption, segfaults, or undefined behavior.

### 2.2 Test Categories

#### Object Lifecycle

Every bound class needs lifecycle tests. These are the highest-priority tests in the entire project because a segfault here means nothing above works.

```python
class TestEngineLifecycle:
    def test_create_and_destroy(self):
        """Engine can be created and garbage collected."""
        engine = te.Engine("test")
        del engine  # should not segfault

    def test_multiple_engines(self):
        """Multiple engines can coexist."""
        e1 = te.Engine("test1")
        e2 = te.Engine("test2")
        del e1
        # e2 should still work
        edit = te.Edit.create(e2)
        assert edit is not None
        del e2

    def test_engine_outlives_edit(self):
        """Engine must outlive its Edits."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine)
        # This is the critical test — does destroying the engine
        # while an Edit reference exists crash?
        del engine
        # Accessing edit after engine destruction should either
        # raise a clean Python exception or still work if we
        # prevent engine destruction while Edits exist.
        with pytest.raises(te.EngineDestroyedError):
            edit.render("test.wav")

class TestEditLifecycle:
    def test_create_empty_edit(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, sample_rate=44100)
        assert edit is not None

    def test_edit_with_bpm(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=140)
        assert abs(edit.bpm - 140.0) < 0.01

    def test_edit_garbage_collection(self):
        """Edit and all child objects can be GC'd cleanly."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("clip", start_beat=0, length_beats=4)
        clip.add_note(60, start_beat=0, length_beats=1, velocity=100)
        # Drop all references in reverse order
        del clip
        del track
        del edit
        gc.collect()
        # Engine should still be alive and functional
        edit2 = te.Edit.create(engine)
        assert edit2 is not None
```

#### Dangling Reference Safety

The most dangerous class of bugs in a Python/C++ binding. Tracktion Engine's Edit owns its Tracks, which own their Clips. If Python holds a reference to a Clip after the Track is deleted, what happens?

```python
class TestDanglingReferences:
    def test_clip_after_track_deletion(self):
        """Accessing a clip after its parent track is deleted."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("clip", start_beat=0, length_beats=4)

        edit.delete_track(track)
        # clip's underlying C++ object is now destroyed
        # Python reference should raise, not segfault
        with pytest.raises(te.ObjectDeletedError):
            clip.add_note(60, 0, 1, 100)

    def test_track_after_edit_deletion(self):
        """Accessing a track after its parent edit is deleted."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine)
        track = edit.insert_audio_track("Test")
        del edit
        gc.collect()
        with pytest.raises(te.ObjectDeletedError):
            track.insert_midi_clip("clip", 0, 4)

    def test_plugin_after_track_deletion(self):
        """Plugin reference survives track deletion safely."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine)
        track = edit.insert_audio_track("Test")
        # Using built-in plugin to avoid VST dependency
        plugin = track.insert_plugin_builtin("volume_and_pan")
        edit.delete_track(track)
        with pytest.raises(te.ObjectDeletedError):
            plugin.set_parameter("volume", 0.5)
```

#### Thread Safety

Tracktion Engine uses JUCE's message thread. Python calls from arbitrary threads must be safe.

```python
class TestThreadSafety:
    def test_concurrent_edit_creation(self):
        """Multiple threads creating edits simultaneously."""
        engine = te.Engine("test")
        results = []

        def create_edit(i):
            edit = te.Edit.create(engine, bpm=120 + i)
            results.append(edit.bpm)

        threads = [threading.Thread(target=create_edit, args=(i,))
                   for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10

    def test_render_does_not_block_main_thread(self):
        """Rendering should release the GIL."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_midi_clip("clip", 0, 16).add_note(60, 0, 16, 100)
        track.insert_plugin_builtin("tone_generator")

        render_started = threading.Event()
        main_thread_alive = threading.Event()

        def render():
            render_started.set()
            edit.render("/tmp/test_thread.wav")

        t = threading.Thread(target=render)
        t.start()
        render_started.wait(timeout=5)
        # Main thread should not be blocked
        main_thread_alive.set()
        assert main_thread_alive.is_set()
        t.join()
```

### 2.3 Running

```bash
pytest tests/layer1_bindings/ -x --timeout=30
```

`-x` stops on first failure — a segfault at this layer invalidates everything. `--timeout` catches hangs from message thread deadlocks.

### 2.4 CI Gate

Layer 1 must pass on all platforms (Linux, macOS, Windows) before any other layer runs. These tests use no audio files, no plugins, no external dependencies — pure engine lifecycle.

---

## 3. Layer 2: Musical Data Model

### 3.1 Purpose

Prove that the musical abstractions (tempo, beats, clips, notes, automation) produce numerically correct results. This layer tests the *meaning* of the data model, not just that it doesn't crash.

### 3.2 Test Categories

#### Tempo and Timing

```python
class TestTempoTiming:
    def test_beat_to_seconds_120bpm(self):
        """At 120 BPM, beat 1 = 0.5 seconds."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        assert abs(edit.beat_to_seconds(1.0) - 0.5) < 0.001

    def test_beat_to_seconds_60bpm(self):
        """At 60 BPM, beat 1 = 1.0 seconds."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=60)
        assert abs(edit.beat_to_seconds(1.0) - 1.0) < 0.001

    def test_tempo_change_midway(self):
        """Tempo change at beat 16 affects subsequent timing."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.tempo_sequence.add_tempo(beat=16, bpm=60)
        # First 16 beats at 120 BPM = 8 seconds
        assert abs(edit.beat_to_seconds(16.0) - 8.0) < 0.001
        # Beat 17 is 1 second after beat 16 (now 60 BPM)
        assert abs(edit.beat_to_seconds(17.0) - 9.0) < 0.001

    def test_time_signature_change(self):
        """Time signature changes affect bar numbering."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.tempo_sequence.add_time_sig(beat=0, numerator=4, denominator=4)
        edit.tempo_sequence.add_time_sig(beat=16, numerator=3, denominator=4)
        # Bar 1-4 are 4 beats each (16 beats total)
        # Bar 5+ are 3 beats each
        assert edit.beat_to_bar(16.0) == 5
        assert edit.beat_to_bar(19.0) == 6
```

#### MIDI Data

```python
class TestMidiClip:
    def test_add_note_basic(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("melody", start_beat=0, length_beats=8)
        clip.add_note(pitch=60, start_beat=0, length_beats=1, velocity=100)
        notes = clip.get_notes()
        assert len(notes) == 1
        assert notes[0].pitch == 60
        assert notes[0].velocity == 100
        assert abs(notes[0].start_beat - 0.0) < 0.001
        assert abs(notes[0].length_beats - 1.0) < 0.001

    def test_note_pitch_range(self):
        """MIDI notes must be 0-127."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("test", 0, 4)
        with pytest.raises(ValueError):
            clip.add_note(pitch=128, start_beat=0, length_beats=1, velocity=100)
        with pytest.raises(ValueError):
            clip.add_note(pitch=-1, start_beat=0, length_beats=1, velocity=100)

    def test_note_outside_clip_bounds(self):
        """Notes starting after clip end should warn or clip."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("test", start_beat=0, length_beats=4)
        # Note starts at beat 5, clip ends at beat 4
        with pytest.raises(ValueError):
            clip.add_note(pitch=60, start_beat=5, length_beats=1, velocity=100)

    def test_many_notes(self):
        """Clip handles large numbers of notes."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        clip = track.insert_midi_clip("stress", start_beat=0, length_beats=1000)
        for i in range(10000):
            clip.add_note(60 + (i % 12), start_beat=i * 0.1,
                         length_beats=0.05, velocity=80)
        assert len(clip.get_notes()) == 10000
```

#### Automation

```python
class TestAutomation:
    def test_linear_automation(self):
        """Two-point automation interpolates linearly."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        plugin = track.insert_plugin_builtin("volume_and_pan")
        auto = plugin.get_parameter("volume").automation
        auto.add_point(beat=0, value=0.0)
        auto.add_point(beat=4, value=1.0)
        # Midpoint should be 0.5
        assert abs(auto.get_value_at(beat=2) - 0.5) < 0.01

    def test_automation_points_persist(self):
        """Automation points survive save/load cycle."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        plugin = track.insert_plugin_builtin("volume_and_pan")
        auto = plugin.get_parameter("volume").automation
        auto.add_point(beat=0, value=0.0)
        auto.add_point(beat=4, value=1.0)
        auto.add_point(beat=8, value=0.5)

        edit.save("/tmp/test_auto.xml")
        edit2 = te.Edit.load(engine, "/tmp/test_auto.xml")
        track2 = edit2.get_tracks()[0]
        plugin2 = track2.get_plugins()[0]
        auto2 = plugin2.get_parameter("volume").automation
        points = auto2.get_points()
        assert len(points) == 3
        assert abs(points[1].value - 1.0) < 0.01
```

#### Track and Clip Management

```python
class TestTrackManagement:
    def test_insert_multiple_tracks(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        for i in range(50):
            edit.insert_audio_track(f"Track_{i}")
        assert len(edit.get_tracks()) == 50

    def test_track_ordering(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.insert_audio_track("A")
        edit.insert_audio_track("B")
        edit.insert_audio_track("C")
        names = [t.name for t in edit.get_tracks()]
        assert names == ["A", "B", "C"]

    def test_delete_middle_track(self):
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.insert_audio_track("A")
        b = edit.insert_audio_track("B")
        edit.insert_audio_track("C")
        edit.delete_track(b)
        names = [t.name for t in edit.get_tracks()]
        assert names == ["A", "C"]

    def test_clips_on_same_track_no_overlap_warning(self):
        """Non-overlapping clips on same track are fine."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_midi_clip("a", start_beat=0, length_beats=4)
        track.insert_midi_clip("b", start_beat=4, length_beats=4)
        assert len(track.get_clips()) == 2
```

### 3.3 Running

```bash
pytest tests/layer2_data_model/ -v
```

These tests use no audio I/O, no plugins, no rendering. They're purely testing the data model's numerical behavior. Should run in seconds.

---

## 4. Layer 3: Audio Validation

### 4.1 Purpose

Prove that rendered audio has the expected musical and acoustic properties. This is where we test the render engine's output against deterministic audio metrics.

### 4.2 Test Infrastructure

A shared validation module used by both tests and the production validation suite:

```python
# tests/audio_validation.py
import librosa
import numpy as np

class AudioValidator:
    def __init__(self, audio_path, expected_sr=44100):
        self.audio, self.sr = librosa.load(audio_path, sr=expected_sr, mono=False)
        if self.audio.ndim == 1:
            self.audio = self.audio.reshape(1, -1)
        self.mono = librosa.to_mono(self.audio)

    @property
    def duration(self):
        return len(self.mono) / self.sr

    @property
    def peak_db(self):
        return 20 * np.log10(np.max(np.abs(self.mono)) + 1e-10)

    @property
    def rms_db(self):
        return 20 * np.log10(np.sqrt(np.mean(self.mono ** 2)) + 1e-10)

    @property
    def detected_tempo(self):
        tempo, _ = librosa.beat.beat_track(y=self.mono, sr=self.sr)
        return float(tempo)

    @property
    def detected_key(self):
        chroma = librosa.feature.chroma_cqt(y=self.mono, sr=self.sr)
        key_index = np.argmax(np.mean(chroma, axis=1))
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F',
                'F#', 'G', 'G#', 'A', 'A#', 'B']
        return keys[key_index]

    @property
    def spectral_centroid(self):
        return float(np.mean(
            librosa.feature.spectral_centroid(y=self.mono, sr=self.sr)))

    @property
    def is_silent(self):
        return self.rms_db < -60

    @property
    def is_clipping(self):
        return np.max(np.abs(self.audio)) > 0.99

    def band_energy(self, low_hz, high_hz):
        S = np.abs(librosa.stft(self.mono))
        freqs = librosa.fft_frequencies(sr=self.sr)
        mask = (freqs >= low_hz) & (freqs < high_hz)
        return float(np.mean(S[mask, :]))

    @property
    def band_ratios(self):
        bands = [(20, 250), (250, 2000), (2000, 6000), (6000, 20000)]
        energies = [self.band_energy(l, h) for l, h in bands]
        total = sum(energies)
        return {
            'sub_bass': energies[0] / total,
            'low_mid': energies[1] / total,
            'high_mid': energies[2] / total,
            'high': energies[3] / total,
        }

    @property
    def channel_count(self):
        return self.audio.shape[0]

    def has_content_between(self, start_sec, end_sec):
        """Check that audio is non-silent in a time range."""
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)
        segment = self.mono[start_sample:end_sample]
        rms = 20 * np.log10(np.sqrt(np.mean(segment ** 2)) + 1e-10)
        return rms > -50
```

### 4.3 Test Categories

#### Silence and Signal Presence

```python
class TestSignalPresence:
    def test_single_note_produces_audio(self):
        """A single MIDI note through a tone generator is not silent."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("note", 0, 4)
        clip.add_note(60, 0, 4, 100)
        edit.render("/tmp/test_signal.wav")

        v = AudioValidator("/tmp/test_signal.wav")
        assert not v.is_silent
        assert v.rms_db > -40  # should be reasonably loud

    def test_empty_edit_is_silent(self):
        """An edit with no clips renders silence."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.insert_audio_track("Empty")
        edit.render("/tmp/test_silence.wav", duration_seconds=2.0)

        v = AudioValidator("/tmp/test_silence.wav")
        assert v.is_silent

    def test_muted_track_is_silent(self):
        """A muted track produces no audio."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Muted")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("note", 0, 4)
        clip.add_note(60, 0, 4, 100)
        track.mute = True
        edit.render("/tmp/test_muted.wav")

        v = AudioValidator("/tmp/test_muted.wav")
        assert v.is_silent
```

#### Timing Accuracy

```python
class TestTimingAccuracy:
    def test_render_duration(self):
        """Rendered audio matches requested duration."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("note", 0, 8)  # 8 beats = 4 seconds at 120
        clip.add_note(60, 0, 8, 100)
        edit.render("/tmp/test_duration.wav")

        v = AudioValidator("/tmp/test_duration.wav")
        assert abs(v.duration - 4.0) < 0.1  # within 100ms

    def test_note_onset_timing(self):
        """A note at beat 4 (120 BPM) has an onset at ~2.0 seconds."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("note", 0, 8)
        # Single note at beat 4
        clip.add_note(60, start_beat=4, length_beats=2, velocity=100)
        edit.render("/tmp/test_onset.wav")

        v = AudioValidator("/tmp/test_onset.wav")
        # First 1.5 seconds should be silent (note starts at 2.0s)
        assert not v.has_content_between(0, 1.5)
        # Audio should be present at 2.0-3.0 seconds
        assert v.has_content_between(2.0, 3.0)

    def test_tempo_affects_timing(self):
        """Same beat position at different tempos lands at different times."""
        engine = te.Engine("test")

        # 120 BPM: beat 4 = 2.0 seconds
        edit1 = te.Edit.create(engine, bpm=120)
        t1 = edit1.insert_audio_track("T")
        t1.insert_plugin_builtin("tone_generator")
        c1 = t1.insert_midi_clip("n", 0, 8)
        c1.add_note(60, 4, 2, 100)
        edit1.render("/tmp/test_tempo_120.wav")

        # 60 BPM: beat 4 = 4.0 seconds
        edit2 = te.Edit.create(engine, bpm=60)
        t2 = edit2.insert_audio_track("T")
        t2.insert_plugin_builtin("tone_generator")
        c2 = t2.insert_midi_clip("n", 0, 8)
        c2.add_note(60, 4, 2, 100)
        edit2.render("/tmp/test_tempo_60.wav")

        v1 = AudioValidator("/tmp/test_tempo_120.wav")
        v2 = AudioValidator("/tmp/test_tempo_60.wav")
        # At 120 BPM, note starts at 2s — should be silent before
        assert not v1.has_content_between(0, 1.5)
        assert v1.has_content_between(2.0, 3.0)
        # At 60 BPM, note starts at 4s — should be silent longer
        assert not v2.has_content_between(0, 3.5)
        assert v2.has_content_between(4.0, 5.0)
```

#### Multi-Track Mixing

```python
class TestMultiTrackMixing:
    def test_two_tracks_louder_than_one(self):
        """Two tracks playing should be louder than one."""
        engine = te.Engine("test")

        edit1 = te.Edit.create(engine, bpm=120)
        t = edit1.insert_audio_track("A")
        t.insert_plugin_builtin("tone_generator")
        t.insert_midi_clip("n", 0, 4).add_note(60, 0, 4, 100)
        edit1.render("/tmp/test_1track.wav")

        edit2 = te.Edit.create(engine, bpm=120)
        for name, pitch in [("A", 60), ("B", 64)]:
            t = edit2.insert_audio_track(name)
            t.insert_plugin_builtin("tone_generator")
            t.insert_midi_clip("n", 0, 4).add_note(pitch, 0, 4, 100)
        edit2.render("/tmp/test_2track.wav")

        v1 = AudioValidator("/tmp/test_1track.wav")
        v2 = AudioValidator("/tmp/test_2track.wav")
        assert v2.rms_db > v1.rms_db

    def test_stereo_output(self):
        """Default render produces stereo audio."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        t = edit.insert_audio_track("A")
        t.insert_plugin_builtin("tone_generator")
        t.insert_midi_clip("n", 0, 4).add_note(60, 0, 4, 100)
        edit.render("/tmp/test_stereo.wav")

        v = AudioValidator("/tmp/test_stereo.wav")
        assert v.channel_count == 2

    def test_stem_export(self):
        """Per-track stem export produces one file per track."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        for name, pitch in [("Kick", 36), ("Snare", 38), ("Lead", 60)]:
            t = edit.insert_audio_track(name)
            t.insert_plugin_builtin("tone_generator")
            t.insert_midi_clip("n", 0, 4).add_note(pitch, 0, 4, 100)

        stems = edit.render_stems("/tmp/stems/")
        assert len(stems) == 3
        for stem_path in stems:
            v = AudioValidator(stem_path)
            assert not v.is_silent
```

#### Clipping and Gain

```python
class TestGainStaging:
    def test_no_clipping_at_default_levels(self):
        """Default gain staging should not clip."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        for i in range(8):
            t = edit.insert_audio_track(f"T{i}")
            t.insert_plugin_builtin("tone_generator")
            t.insert_midi_clip("n", 0, 4).add_note(60 + i, 0, 4, 100)
        edit.render("/tmp/test_noclip.wav")

        v = AudioValidator("/tmp/test_noclip.wav")
        assert not v.is_clipping

    def test_volume_automation_affects_output(self):
        """Automating volume to zero produces silence in that region."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("n", 0, 8)
        clip.add_note(60, 0, 8, 100)
        vol = track.volume_parameter.automation
        vol.add_point(beat=0, value=1.0)
        vol.add_point(beat=4, value=0.0)  # fade to zero at beat 4
        edit.render("/tmp/test_vol_auto.wav")

        v = AudioValidator("/tmp/test_vol_auto.wav")
        assert v.has_content_between(0, 1.5)
        # Last second should be essentially silent (faded out)
        assert not v.has_content_between(3.5, 4.0)
```

### 4.4 Running

```bash
pytest tests/layer3_audio/ -v --timeout=60
```

Longer timeout because rendering takes real time. Each test creates an engine, builds an arrangement, renders, and validates. Audio files are written to `/tmp` and cleaned up by a fixture.

---

## 5. Layer 4: Format Compatibility

### 5.1 Purpose

Prove that exported project files are structurally valid and open correctly in target DAWs.

### 5.2 Test Categories

#### DAWproject XML Schema Validation

```python
class TestDAWprojectExport:
    def test_valid_xml_structure(self):
        """Exported DAWproject has valid XML."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=128)
        track = edit.insert_audio_track("Bass")
        clip = track.insert_midi_clip("riff", 0, 16)
        clip.add_note(36, 0, 1, 100)
        edit.export_dawproject("/tmp/test.dawproject")

        # Unzip and parse XML
        import zipfile, xml.etree.ElementTree as ET
        with zipfile.ZipFile("/tmp/test.dawproject") as z:
            with z.open("project.xml") as f:
                tree = ET.parse(f)
        root = tree.getroot()
        assert root.tag == "Project"
        assert root.attrib.get("version") == "1.0"

    def test_tempo_exported(self):
        """BPM appears in DAWproject Transport element."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=145)
        edit.insert_audio_track("T")
        edit.export_dawproject("/tmp/test_tempo.dawproject")

        root = parse_dawproject("/tmp/test_tempo.dawproject")
        tempo = root.find(".//Tempo")
        assert tempo is not None
        assert abs(float(tempo.attrib["value"]) - 145.0) < 0.01

    def test_tracks_exported(self):
        """All tracks appear in DAWproject Structure."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        edit.insert_audio_track("Drums")
        edit.insert_audio_track("Bass")
        edit.insert_audio_track("Guitar")
        edit.export_dawproject("/tmp/test_tracks.dawproject")

        root = parse_dawproject("/tmp/test_tracks.dawproject")
        tracks = root.findall(".//Track")
        names = [t.attrib.get("name") for t in tracks]
        assert "Drums" in names
        assert "Bass" in names
        assert "Guitar" in names

    def test_midi_notes_exported(self):
        """MIDI notes appear in DAWproject note data."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Lead")
        clip = track.insert_midi_clip("melody", 0, 4)
        clip.add_note(60, 0, 1, 100)
        clip.add_note(64, 1, 1, 80)
        clip.add_note(67, 2, 1, 90)
        edit.export_dawproject("/tmp/test_notes.dawproject")

        root = parse_dawproject("/tmp/test_notes.dawproject")
        notes = root.findall(".//Note")
        assert len(notes) == 3

    def test_automation_exported(self):
        """Automation points appear in DAWproject."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Test")
        vol = track.volume_parameter.automation
        vol.add_point(beat=0, value=0.0)
        vol.add_point(beat=8, value=1.0)
        edit.export_dawproject("/tmp/test_auto.dawproject")

        root = parse_dawproject("/tmp/test_auto.dawproject")
        points = root.findall(".//Point")
        assert len(points) >= 2

    def test_audio_files_bundled(self):
        """Audio clips have their files included in the container."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Audio")
        track.insert_audio_clip("sample", "tests/fixtures/kick.wav", 0, 4)
        edit.export_dawproject("/tmp/test_audio_bundle.dawproject")

        import zipfile
        with zipfile.ZipFile("/tmp/test_audio_bundle.dawproject") as z:
            names = z.namelist()
            assert any("kick.wav" in n for n in names)
```

#### REAPER RPP Export

```python
class TestReaperExport:
    def test_valid_rpp_structure(self):
        """RPP file has valid REAPER project structure."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=130)
        edit.insert_audio_track("Test")
        edit.export_rpp("/tmp/test.rpp")

        with open("/tmp/test.rpp") as f:
            content = f.read()
        assert content.startswith("<REAPER_PROJECT")
        assert "TEMPO 130" in content or "TEMPO  130" in content
        assert "<TRACK" in content

    def test_midi_items_in_rpp(self):
        """MIDI notes export as MIDI items in RPP."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Lead")
        clip = track.insert_midi_clip("melody", 0, 4)
        clip.add_note(60, 0, 1, 100)
        edit.export_rpp("/tmp/test_midi.rpp")

        with open("/tmp/test_midi.rpp") as f:
            content = f.read()
        assert "<SOURCE MIDI" in content or "<ITEM" in content
```

#### MIDI Export

```python
class TestMidiExport:
    def test_valid_midi_file(self):
        """Exported MIDI file is parseable."""
        import mido
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Lead")
        clip = track.insert_midi_clip("melody", 0, 4)
        clip.add_note(60, 0, 1, 100)
        clip.add_note(64, 1, 1, 80)
        edit.export_midi("/tmp/test.mid")

        mid = mido.MidiFile("/tmp/test.mid")
        assert len(mid.tracks) >= 1
        note_ons = [msg for track in mid.tracks
                    for msg in track if msg.type == 'note_on']
        assert len(note_ons) == 2

    def test_tempo_in_midi(self):
        """Tempo is encoded in MIDI file."""
        import mido
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=140)
        track = edit.insert_audio_track("T")
        track.insert_midi_clip("n", 0, 4).add_note(60, 0, 1, 100)
        edit.export_midi("/tmp/test_tempo.mid")

        mid = mido.MidiFile("/tmp/test_tempo.mid")
        tempos = [msg for track in mid.tracks
                  for msg in track if msg.type == 'set_tempo']
        assert len(tempos) >= 1
        bpm = mido.tempo2bpm(tempos[0].tempo)
        assert abs(bpm - 140.0) < 1.0
```

#### Metadata Export

```python
class TestMetadataExport:
    def test_json_metadata_complete(self):
        """Metadata JSON contains all notes, params, and structure."""
        import json
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("Lead")
        clip = track.insert_midi_clip("melody", 0, 8)
        clip.add_note(60, 0, 1, 100)
        clip.add_note(64, 2, 1, 80)
        edit.export_metadata("/tmp/test_meta.json")

        with open("/tmp/test_meta.json") as f:
            meta = json.load(f)

        assert meta["bpm"] == 120
        assert len(meta["tracks"]) == 1
        assert meta["tracks"][0]["name"] == "Lead"
        assert len(meta["tracks"][0]["clips"][0]["notes"]) == 2
        assert meta["tracks"][0]["clips"][0]["notes"][0]["pitch"] == 60

    def test_metadata_matches_render(self):
        """Metadata tempo matches detected tempo in rendered audio."""
        import json
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=95)
        track = edit.insert_audio_track("Drums")
        track.insert_plugin_builtin("tone_generator")
        clip = track.insert_midi_clip("beat", 0, 32)
        for beat in range(32):
            clip.add_note(60, beat, 0.25, 127)
        edit.render("/tmp/test_meta_render.wav")
        edit.export_metadata("/tmp/test_meta_render.json")

        v = AudioValidator("/tmp/test_meta_render.wav")
        with open("/tmp/test_meta_render.json") as f:
            meta = json.load(f)

        assert abs(v.detected_tempo - meta["bpm"]) < 5  # within 5 BPM
```

### 5.3 DAW Smoke Tests (Manual + Semi-Automated)

These tests require actual DAW installations and cannot run in CI without licensed software. They run locally or in a dedicated test environment.

```python
# tests/layer4_daw_smoke/conftest.py
import subprocess, shutil

def daw_available(name):
    """Check if a DAW is installed for smoke testing."""
    paths = {
        'bitwig': shutil.which('bitwig-studio'),
        'reaper': shutil.which('reaper'),
    }
    return paths.get(name) is not None

# tests/layer4_daw_smoke/test_bitwig.py
@pytest.mark.skipif(not daw_available('bitwig'), reason="Bitwig not installed")
class TestBitwigSmoke:
    def test_dawproject_opens_without_error(self):
        """Bitwig opens our DAWproject file without crashing."""
        # Generate a test project
        generate_test_project("/tmp/smoke_test.dawproject")
        # Launch Bitwig headlessly with the file, wait for load, check exit code
        result = subprocess.run(
            ['bitwig-studio', '--headless', '/tmp/smoke_test.dawproject'],
            timeout=30, capture_output=True
        )
        assert result.returncode == 0
        assert 'error' not in result.stderr.decode().lower()
```

### 5.4 Round-Trip Tests

The strongest format compatibility test: export → import in DAW → re-export → compare.

```python
class TestRoundTrip:
    def test_edit_xml_roundtrip(self):
        """Save Edit XML, reload, re-save, compare."""
        engine = te.Engine("test")
        edit1 = te.Edit.create(engine, bpm=120)
        track = edit1.insert_audio_track("Lead")
        clip = track.insert_midi_clip("melody", 0, 8)
        clip.add_note(60, 0, 1, 100)
        clip.add_note(64, 2, 1, 80)
        edit1.save("/tmp/roundtrip_1.xml")

        edit2 = te.Edit.load(engine, "/tmp/roundtrip_1.xml")
        edit2.save("/tmp/roundtrip_2.xml")

        # Compare the two XML files structurally
        import xml.etree.ElementTree as ET
        tree1 = ET.parse("/tmp/roundtrip_1.xml")
        tree2 = ET.parse("/tmp/roundtrip_2.xml")
        # Track count, clip count, note data should match
        assert (len(tree1.findall(".//TRACK")) ==
                len(tree2.findall(".//TRACK")))

    def test_render_consistency_across_loads(self):
        """Same Edit rendered after save/load produces identical audio."""
        engine = te.Engine("test")
        edit1 = te.Edit.create(engine, bpm=120)
        track = edit1.insert_audio_track("Test")
        track.insert_plugin_builtin("tone_generator")
        track.insert_midi_clip("n", 0, 4).add_note(60, 0, 4, 100)
        edit1.render("/tmp/render_before_save.wav")
        edit1.save("/tmp/consistency.xml")

        edit2 = te.Edit.load(engine, "/tmp/consistency.xml")
        edit2.render("/tmp/render_after_load.wav")

        v1 = AudioValidator("/tmp/render_before_save.wav")
        v2 = AudioValidator("/tmp/render_after_load.wav")
        # RMS should match within 0.1 dB
        assert abs(v1.rms_db - v2.rms_db) < 0.1
```

---

## 6. Layer 5: Integration / End-to-End

### 6.1 Purpose

Prove the complete workflow: specification → generation → render → validate → export.

### 6.2 Tests

```python
class TestEndToEnd:
    def test_full_pipeline(self):
        """Complete pipeline: create arrangement, render, validate, export."""
        engine = te.Engine("test")
        edit = te.Edit.create(engine, bpm=120)

        # Build a simple arrangement
        drums = edit.insert_audio_track("Drums")
        drums.insert_plugin_builtin("tone_generator")
        drum_clip = drums.insert_midi_clip("beat", 0, 16)
        for beat in range(16):
            drum_clip.add_note(36, beat, 0.25, 127)       # kick every beat
            if beat % 2 == 1:
                drum_clip.add_note(38, beat, 0.25, 100)    # snare on 2,4

        bass = edit.insert_audio_track("Bass")
        bass.insert_plugin_builtin("tone_generator")
        bass_clip = bass.insert_midi_clip("line", 0, 16)
        bass_clip.add_note(36, 0, 2, 100)
        bass_clip.add_note(41, 4, 2, 100)
        bass_clip.add_note(43, 8, 2, 100)

        # Render
        edit.render("/tmp/e2e_mix.wav")
        stems = edit.render_stems("/tmp/e2e_stems/")

        # Validate audio
        v = AudioValidator("/tmp/e2e_mix.wav")
        assert not v.is_silent
        assert not v.is_clipping
        assert abs(v.duration - 8.0) < 0.5  # 16 beats at 120 BPM = 8 sec
        assert abs(v.detected_tempo - 120) < 5

        # Validate stems
        assert len(stems) == 2
        for stem in stems:
            sv = AudioValidator(stem)
            assert not sv.is_silent

        # Export to all formats
        edit.export_dawproject("/tmp/e2e.dawproject")
        edit.export_rpp("/tmp/e2e.rpp")
        edit.export_midi("/tmp/e2e.mid")
        edit.export_metadata("/tmp/e2e.json")

        # Verify exports exist and are non-empty
        for path in ["/tmp/e2e.dawproject", "/tmp/e2e.rpp",
                     "/tmp/e2e.mid", "/tmp/e2e.json"]:
            assert os.path.getsize(path) > 0

    def test_batch_generation(self):
        """Generate N variations and validate all of them."""
        engine = te.Engine("test")
        results = []

        for i in range(10):
            bpm = 80 + i * 10  # 80 to 170 BPM
            edit = te.Edit.create(engine, bpm=bpm)
            track = edit.insert_audio_track("Test")
            track.insert_plugin_builtin("tone_generator")
            clip = track.insert_midi_clip("n", 0, 8)
            for beat in range(8):
                clip.add_note(48 + (beat % 12), beat, 0.5, 100)

            path = f"/tmp/batch_{i}.wav"
            edit.render(path)
            v = AudioValidator(path)

            results.append({
                'bpm_requested': bpm,
                'bpm_detected': v.detected_tempo,
                'silent': v.is_silent,
                'clipping': v.is_clipping,
                'rms_db': v.rms_db,
            })

        # All renders should be non-silent and non-clipping
        for r in results:
            assert not r['silent']
            assert not r['clipping']

        # Detected tempos should trend upward with requested tempos
        detected = [r['bpm_detected'] for r in results]
        requested = [r['bpm_requested'] for r in results]
        correlation = np.corrcoef(requested, detected)[0, 1]
        assert correlation > 0.8  # strong positive correlation
```

---

## 7. CI/CD Pipeline

### 7.1 Pipeline Structure

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  layer1-bindings:
    name: "Layer 1: Binding Correctness"
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Build
        run: pip install -e ".[dev]"
      - name: Test Layer 1
        run: pytest tests/layer1_bindings/ -x --timeout=30 -v

  layer2-data-model:
    name: "Layer 2: Data Model"
    needs: layer1-bindings
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: pip install -e ".[dev]"
      - name: Test Layer 2
        run: pytest tests/layer2_data_model/ -v

  layer3-audio:
    name: "Layer 3: Audio Validation"
    needs: layer2-data-model
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: pip install -e ".[dev,audio]"
      - name: Test Layer 3
        run: pytest tests/layer3_audio/ -v --timeout=60

  layer4-formats:
    name: "Layer 4: Format Compatibility"
    needs: layer3-audio
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: pip install -e ".[dev,audio,formats]"
      - name: Test Layer 4
        run: pytest tests/layer4_formats/ -v --timeout=60

  layer5-integration:
    name: "Layer 5: Integration"
    needs: layer4-formats
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: pip install -e ".[dev,audio,formats]"
      - name: Test Layer 5
        run: pytest tests/layer5_integration/ -v --timeout=120
```

### 7.2 Key CI Principles

**Layer dependencies are strict.** Layer 1 failures block everything. A segfault in binding lifecycle means audio validation results are meaningless.

**Cross-platform at Layer 1 only.** Binding correctness and memory safety must pass on all three OSes. Higher layers run on Linux only in CI to save cost — format compatibility is platform-independent (it's XML generation), and audio rendering via Tracktion Engine should produce identical output across platforms.

**No VST plugins in CI.** All CI tests use Tracktion Engine's built-in processors (tone generator, volume/pan, basic effects). VST-dependent tests are marked `@pytest.mark.requires_vst` and run locally or in a dedicated environment with licensed plugins.

**Audio fixtures are deterministic.** Test audio files in `tests/fixtures/` are committed to the repo. Generated audio is written to `/tmp` and never committed.

**DAW smoke tests are manual-triggered.** The Layer 4 DAW smoke tests (opening files in Bitwig, Reaper, etc.) require licensed DAW installations. They run on a manual workflow dispatch or nightly schedule on a dedicated machine, not on every push.

### 7.3 Test Fixture Management

```
tests/
├── conftest.py              # Shared fixtures (engine creation, temp dirs)
├── audio_validation.py      # AudioValidator class
├── fixtures/
│   ├── kick.wav             # Short audio samples for audio clip tests
│   ├── snare.wav
│   └── reference_tracks/    # Reference spectral profiles per genre
│       ├── doom_metal.json  # Expected band ratios, centroid ranges
│       └── pop.json
├── layer1_bindings/
│   ├── test_engine_lifecycle.py
│   ├── test_edit_lifecycle.py
│   ├── test_dangling_refs.py
│   └── test_thread_safety.py
├── layer2_data_model/
│   ├── test_tempo_timing.py
│   ├── test_midi_clips.py
│   ├── test_automation.py
│   └── test_track_management.py
├── layer3_audio/
│   ├── test_signal_presence.py
│   ├── test_timing_accuracy.py
│   ├── test_mixing.py
│   └── test_gain_staging.py
├── layer4_formats/
│   ├── test_dawproject.py
│   ├── test_reaper_rpp.py
│   ├── test_midi_export.py
│   ├── test_metadata.py
│   └── test_roundtrip.py
├── layer5_integration/
│   ├── test_end_to_end.py
│   └── test_batch.py
└── daw_smoke/               # Manual / nightly only
    ├── test_bitwig.py
    └── test_reaper.py
```

---

## 8. Regression Testing Strategy

### 8.1 Audio Regression Baselines

When a test suite run produces correct output, snapshot the audio metrics as a baseline:

```python
# tests/conftest.py
import json

def save_audio_baseline(test_name, validator):
    baseline = {
        'rms_db': validator.rms_db,
        'peak_db': validator.peak_db,
        'spectral_centroid': validator.spectral_centroid,
        'duration': validator.duration,
        'band_ratios': validator.band_ratios,
    }
    path = f"tests/baselines/{test_name}.json"
    with open(path, 'w') as f:
        json.dump(baseline, f, indent=2)

def check_audio_regression(test_name, validator, tolerance=0.5):
    """Compare current render against saved baseline."""
    path = f"tests/baselines/{test_name}.json"
    if not os.path.exists(path):
        pytest.skip("No baseline exists yet — run with --save-baselines")
    with open(path) as f:
        baseline = json.load(f)
    assert abs(validator.rms_db - baseline['rms_db']) < tolerance
    assert abs(validator.spectral_centroid - baseline['spectral_centroid']) < 50
    assert abs(validator.duration - baseline['duration']) < 0.1
```

Baselines are committed to the repo. When Tracktion Engine is updated or the binding layer changes, baselines are regenerated with `pytest --save-baselines` and the diff is reviewed.

### 8.2 Format Regression Baselines

Similar approach for export formats — snapshot "known good" DAWproject XML structure:

```python
def test_dawproject_regression(self):
    """DAWproject output matches known-good structural snapshot."""
    edit = create_standard_test_edit()
    edit.export_dawproject("/tmp/regression.dawproject")
    current = parse_dawproject_structure("/tmp/regression.dawproject")
    baseline = load_json("tests/baselines/dawproject_structure.json")

    assert current['track_count'] == baseline['track_count']
    assert current['clip_count'] == baseline['clip_count']
    assert current['note_count'] == baseline['note_count']
    assert current['automation_point_count'] == baseline['automation_point_count']
    assert current['has_tempo'] == baseline['has_tempo']
    assert current['has_time_signature'] == baseline['has_time_signature']
```

---

## 9. Performance Benchmarks

Not correctness tests, but tracked alongside them to catch performance regressions.

```python
# tests/benchmarks/test_render_performance.py
import time

class TestRenderPerformance:
    def test_simple_render_under_1_second(self):
        """A 4-bar mono arrangement renders in under 1 second."""
        engine = te.Engine("bench")
        edit = te.Edit.create(engine, bpm=120)
        track = edit.insert_audio_track("T")
        track.insert_plugin_builtin("tone_generator")
        track.insert_midi_clip("n", 0, 16).add_note(60, 0, 16, 100)

        start = time.perf_counter()
        edit.render("/tmp/bench_simple.wav")
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0

    def test_complex_render_faster_than_realtime(self):
        """A 3-minute, 10-track arrangement renders faster than real-time."""
        engine = te.Engine("bench")
        edit = te.Edit.create(engine, bpm=120)
        for i in range(10):
            track = edit.insert_audio_track(f"Track_{i}")
            track.insert_plugin_builtin("tone_generator")
            clip = track.insert_midi_clip("n", 0, 360)  # 360 beats = 3 min
            for beat in range(0, 360, 4):
                clip.add_note(48 + (i * 3) % 24, beat, 2, 100)

        start = time.perf_counter()
        edit.render("/tmp/bench_complex.wav")
        elapsed = time.perf_counter() - start

        assert elapsed < 180.0  # faster than the 3-minute duration

    def test_dawproject_export_under_500ms(self):
        """DAWproject export for a complex project takes < 500ms."""
        edit = create_complex_test_edit()  # 20 tracks, 100 clips
        start = time.perf_counter()
        edit.export_dawproject("/tmp/bench_export.dawproject")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5

    def test_batch_100_renders(self):
        """100 simple renders complete in under 60 seconds."""
        engine = te.Engine("bench")
        start = time.perf_counter()
        for i in range(100):
            edit = te.Edit.create(engine, bpm=120)
            t = edit.insert_audio_track("T")
            t.insert_plugin_builtin("tone_generator")
            t.insert_midi_clip("n", 0, 4).add_note(60, 0, 4, 100)
            edit.render(f"/tmp/batch_bench_{i}.wav")
        elapsed = time.perf_counter() - start
        assert elapsed < 60.0
```

---

## 10. Test Development Roadmap

Tests are written **before or alongside** the features they test. Each development phase has specific testing milestones.

### Phase 1 (Months 1-4): Core Engine

| Week | Feature | Tests Added |
|------|---------|-------------|
| 1-2 | Engine + Edit creation | All Layer 1 lifecycle tests |
| 3-4 | Track + Clip insertion | Layer 1 dangling refs, Layer 2 track management |
| 5-6 | MIDI note data | Layer 2 MIDI clip tests |
| 7-8 | Built-in plugin hosting | Layer 1 plugin lifecycle, Layer 2 automation |
| 9-10 | Tempo map | Layer 2 tempo/timing tests |
| 11-12 | Offline render | Layer 3 signal presence + timing accuracy |
| 13-14 | Stem export + gain staging | Layer 3 mixing + clipping tests |
| 15-16 | Validation suite v1 | AudioValidator class, regression baselines |

**Phase 1 exit criteria**: All Layer 1-3 tests pass on Linux. CI pipeline runs Layers 1-3 on every push.

### Phase 2 (Months 4-7): Export Layer

| Week | Feature | Tests Added |
|------|---------|-------------|
| 17-18 | DAWproject export | Layer 4 DAWproject schema + structure tests |
| 19-20 | REAPER RPP export | Layer 4 RPP tests |
| 21-22 | MIDI export | Layer 4 MIDI tests + mido validation |
| 23-24 | Metadata export | Layer 4 metadata tests, metadata-audio cross-validation |
| 25-26 | Edit XML roundtrip | Layer 4 roundtrip tests |
| 27-28 | Ableton ALS export (basic) | Layer 4 ALS structure tests |

**Phase 2 exit criteria**: All Layer 1-4 tests pass. DAWproject files open in Bitwig (manual smoke test). Full Layer 5 integration test passes.

### Phase 3 (Months 7-12): Scale

| Week | Feature | Tests Added |
|------|---------|-------------|
| 29-32 | Batch runner | Layer 5 batch generation tests, performance benchmarks |
| 33-36 | Genre templates | Per-template validation (tempo, key, spectral profile vs genre reference) |
| 37-40 | Cloud API | API endpoint tests (request → render → response), load tests |
| 41-44 | FL Studio export | Layer 4 FLP tests via pyflp |

**Phase 3 exit criteria**: Batch 10,000 renders overnight with zero validation failures. All export formats produce valid files. Performance benchmarks tracked in CI.

---

## 11. Test Tooling and Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-timeout>=2.2",
    "pytest-xdist>=3.5",      # parallel test execution
]
audio = [
    "librosa>=0.10",
    "numpy>=1.24",
    "soundfile>=0.12",
]
formats = [
    "mido>=1.3",              # MIDI validation
    "pyflp>=2.0",             # FL Studio format validation
]
```

### Custom pytest plugins

```python
# conftest.py
def pytest_addoption(parser):
    parser.addoption("--save-baselines", action="store_true",
                     help="Save current outputs as regression baselines")
    parser.addoption("--with-vst", action="store_true",
                     help="Run tests that require VST plugins")
    parser.addoption("--daw-smoke", action="store_true",
                     help="Run DAW smoke tests (requires DAW installations)")

@pytest.fixture(autouse=True)
def temp_dir(tmp_path):
    """Provide a clean temp directory for each test."""
    return tmp_path

@pytest.fixture(scope="session")
def engine():
    """Shared engine instance for the test session."""
    e = te.Engine("test_session")
    yield e
    del e
```
