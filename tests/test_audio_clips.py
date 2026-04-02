"""Tests for audio clip support (Section 1.2).

Verifies:
- Audio clip insertion, name, file path, timing
- Gain get/set (linear)
- Loop get/set
- Lifetime safety (keep_alive)
- Rendering produces non-silent output
"""

import gc
import math
import os
import struct
import wave

import dawsmith
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sine_wav(tmp_path_factory):
    """Generate a 1-second 440 Hz sine wave WAV (44100 Hz, 16-bit mono)."""
    path = str(tmp_path_factory.mktemp("audio") / "sine_440hz.wav")
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0
    amplitude = 0.8
    num_samples = int(sample_rate * duration)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(num_samples):
            t = i / sample_rate
            sample = amplitude * math.sin(2.0 * math.pi * frequency * t)
            wf.writeframes(struct.pack("<h", int(sample * 32767)))

    return path


# ---------------------------------------------------------------------------
# Basic insertion and getters
# ---------------------------------------------------------------------------

def test_insert_audio_clip(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("MyAudio", sine_wav, 0.0, 4.0)
    assert clip is not None


def test_audio_clip_get_name(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("DrumLoop", sine_wav, 0.0, 4.0)
    assert clip.get_name() == "DrumLoop"


def test_audio_clip_get_file_path(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    # Normalize for cross-platform comparison
    assert os.path.normpath(clip.get_file_path()) == os.path.normpath(sine_wav)


def test_audio_clip_get_start_beat(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 2.0, 4.0)
    assert abs(clip.get_start_beat() - 2.0) < 0.01


def test_audio_clip_get_length_beats(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 8.0)
    assert abs(clip.get_length_beats() - 8.0) < 0.01


def test_audio_clip_start_beat_zero(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    assert abs(clip.get_start_beat()) < 0.01


# ---------------------------------------------------------------------------
# Gain
# ---------------------------------------------------------------------------

def test_audio_clip_default_gain(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    assert abs(clip.get_gain() - 1.0) < 0.01


def test_audio_clip_set_get_gain(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    clip.set_gain(0.5)
    assert abs(clip.get_gain() - 0.5) < 0.01


def test_audio_clip_gain_zero(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    clip.set_gain(0.0)
    assert clip.get_gain() < 0.001


def test_audio_clip_gain_boost(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    clip.set_gain(2.0)
    assert abs(clip.get_gain() - 2.0) < 0.05


# ---------------------------------------------------------------------------
# Looping
# ---------------------------------------------------------------------------

def test_audio_clip_default_loop(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    assert clip.get_loop() is False


def test_audio_clip_set_get_loop(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("A", sine_wav, 0.0, 4.0)
    clip.set_loop(True)
    assert clip.get_loop() is True
    clip.set_loop(False)
    assert clip.get_loop() is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_audio_clip_nonexistent_file(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    with pytest.raises(RuntimeError, match="Audio file not found"):
        track.insert_audio_clip("Bad", "/nonexistent/path.wav", 0.0, 4.0)


# ---------------------------------------------------------------------------
# Coexistence
# ---------------------------------------------------------------------------

def test_audio_clip_on_multiple_tracks(engine, sine_wav):
    edit = engine.create_edit()
    t1 = edit.insert_audio_track("T1")
    t2 = edit.insert_audio_track("T2")
    c1 = t1.insert_audio_clip("A1", sine_wav, 0.0, 4.0)
    c2 = t2.insert_audio_clip("A2", sine_wav, 0.0, 4.0)
    assert c1.get_name() == "A1"
    assert c2.get_name() == "A2"


def test_audio_clip_and_midi_clip_coexist(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    midi = track.insert_midi_clip("Midi", 0.0, 4.0)
    audio = track.insert_audio_clip("Audio", sine_wav, 4.0, 4.0)
    assert midi.get_name() == "Midi"
    assert audio.get_name() == "Audio"


# ---------------------------------------------------------------------------
# Lifetime safety
# ---------------------------------------------------------------------------

def test_audio_clip_survives_track_deletion(engine, sine_wav):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_audio_clip("Survivor", sine_wav, 0.0, 4.0)
    del track
    gc.collect()

    assert clip.get_name() == "Survivor"
    clip.set_gain(0.5)
    assert abs(clip.get_gain() - 0.5) < 0.01
    clip.set_loop(True)
    assert clip.get_loop() is True


def test_audio_clip_deep_hierarchy(engine, sine_wav):
    eng = dawsmith.create_engine()
    edit = eng.create_edit()
    track = edit.insert_audio_track("Deep")
    clip = track.insert_audio_clip("Leaf", sine_wav, 0.0, 4.0)

    del eng, edit, track
    gc.collect()

    assert clip.get_name() == "Leaf"
    assert abs(clip.get_gain() - 1.0) < 0.01


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _read_wav_samples(path):
    """Read a WAV file and return (num_channels, frames, max_amplitude)."""
    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    total = n_frames * n_channels
    if sampwidth == 2:
        samples = struct.unpack(f"<{total}h", raw)
    elif sampwidth == 3:
        # 24-bit little-endian: unpack each 3-byte group as signed int
        samples = []
        for i in range(total):
            b = raw[i * 3 : i * 3 + 3]
            val = int.from_bytes(b, byteorder="little", signed=True)
            samples.append(val)
    else:
        samples = [0]

    return n_channels, n_frames, max(abs(s) for s in samples)


def test_render_audio_clip_not_silent(engine, sine_wav, tmp_path):
    edit = engine.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Audio")
    track.insert_audio_clip("sine", sine_wav, 0.0, 4.0)

    wav_path = str(tmp_path / "audio_clip_render.wav")
    opts = dawsmith.RenderOptions()
    opts.output_path = wav_path
    opts.sample_rate = 44100
    opts.bit_depth = 16
    opts.end_seconds = 1.0
    edit.render(opts)

    assert os.path.isfile(wav_path)
    assert os.path.getsize(wav_path) > 100
    _, _, max_amp = _read_wav_samples(wav_path)
    assert max_amp > 100, "Rendered audio clip should not be silent"
