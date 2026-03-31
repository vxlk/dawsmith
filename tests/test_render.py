import os
import wave
import struct
import dawsmith
import pytest


def _read_wav_samples(path):
    """Read WAV file and return (sample_rate, num_frames, max_amplitude)."""
    with wave.open(path, "rb") as f:
        sr = f.getframerate()
        nframes = f.getnframes()
        sampwidth = f.getsampwidth()
        raw = f.readframes(nframes)

    if sampwidth == 2:
        fmt = f"<{len(raw) // 2}h"
        samples = struct.unpack(fmt, raw)
    elif sampwidth == 3:
        # 24-bit: unpack manually
        samples = []
        for i in range(0, len(raw), 3):
            val = int.from_bytes(raw[i : i + 3], "little", signed=True)
            samples.append(val)
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    max_amp = max(abs(s) for s in samples) if samples else 0
    return sr, nframes, max_amp


def _render_note(engine_with_plugins, first_instrument, tmp_path,
                 pitch=60, bpm=120.0, filename="test.wav"):
    """Helper: render a single note and return the WAV path."""
    edit = engine_with_plugins.create_edit(bpm=bpm)
    track = edit.insert_audio_track("Synth")
    track.insert_plugin(first_instrument.identifier)

    clip = track.insert_midi_clip("clip", 0.0, 4.0)
    clip.add_note(pitch, 0.0, 4.0, velocity=100)

    wav_path = str(tmp_path / filename)
    opts = dawsmith.RenderOptions()
    opts.output_path = wav_path
    opts.sample_rate = 44100
    opts.bit_depth = 16
    opts.end_seconds = 2.5  # 4 beats at 120 BPM = 2s, plus tail
    edit.render(opts)
    return wav_path


def test_render_produces_wav(engine_with_plugins, first_instrument, tmp_path):
    wav_path = _render_note(engine_with_plugins, first_instrument, tmp_path)
    assert os.path.isfile(wav_path), "WAV file was not created"
    assert os.path.getsize(wav_path) > 100, "WAV file is too small"


def test_render_correct_sample_rate(engine_with_plugins, first_instrument,
                                     tmp_path):
    wav_path = _render_note(engine_with_plugins, first_instrument, tmp_path)
    sr, _, _ = _read_wav_samples(wav_path)
    assert sr in (44100, 48000), f"Unexpected sample rate: {sr}"


def test_render_not_silent(engine_with_plugins, first_instrument, tmp_path):
    wav_path = _render_note(engine_with_plugins, first_instrument, tmp_path)
    _, _, max_amp = _read_wav_samples(wav_path)
    assert max_amp > 100, (
        f"Rendered audio appears silent (max amplitude: {max_amp})"
    )


def test_render_has_reasonable_duration(engine_with_plugins, first_instrument,
                                        tmp_path):
    wav_path = _render_note(engine_with_plugins, first_instrument, tmp_path)
    sr, nframes, _ = _read_wav_samples(wav_path)
    duration = nframes / sr
    # 4 beats at 120 BPM = 2s; render may include tail
    assert 1.0 < duration < 10.0, (
        f"Duration {duration:.2f}s outside expected range 1-10s"
    )


def test_render_different_notes_differ(engine_with_plugins, first_instrument,
                                        tmp_path):
    wav_c4 = _render_note(engine_with_plugins, first_instrument, tmp_path,
                          pitch=60, filename="c4.wav")
    wav_c5 = _render_note(engine_with_plugins, first_instrument, tmp_path,
                          pitch=72, filename="c5.wav")

    with open(wav_c4, "rb") as f:
        data_c4 = f.read()
    with open(wav_c5, "rb") as f:
        data_c5 = f.read()

    assert data_c4 != data_c5, (
        "WAVs for C4 and C5 are identical — plugin may not be responding to MIDI"
    )
