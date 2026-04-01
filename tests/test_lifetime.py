"""Tests for object lifetime safety (Section 1.1).

Verifies that:
- keep_alive prevents premature GC of parent objects
- Shared JUCE init keeps JUCE alive across Engine/Edit lifetimes
- Create/destroy cycles don't leak or crash
- GC ordering doesn't cause segfaults
- Conditional MessageManager pumping works correctly for play/stop
"""

import gc
import dawsmith
import pytest


# ---------------------------------------------------------------------------
# keep_alive: Engine stays alive while Edit exists
# ---------------------------------------------------------------------------

def test_edit_survives_engine_variable_deletion():
    """del engine should NOT destroy Engine while an Edit holds keep_alive ref."""
    engine = dawsmith.create_engine()
    edit = engine.create_edit(bpm=120.0)
    del engine  # Engine kept alive by edit's keep_alive
    gc.collect()

    # Edit should still be fully functional
    track = edit.insert_audio_track("Test")
    assert track.get_name() == "Test"
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 1.0, velocity=100)


def test_edit_survives_engine_reassignment():
    """Reassigning engine variable should NOT affect existing edits."""
    engine = dawsmith.create_engine()
    edit = engine.create_edit(bpm=90.0)
    engine = dawsmith.create_engine()  # reassign -- old engine kept alive
    gc.collect()

    edit.set_tempo(140.0)
    track = edit.insert_audio_track("Survives")
    assert track.get_name() == "Survives"


# ---------------------------------------------------------------------------
# keep_alive: Edit stays alive while Track exists
# ---------------------------------------------------------------------------

def test_track_survives_edit_variable_deletion():
    """del edit should NOT destroy Edit while a Track holds keep_alive ref."""
    engine = dawsmith.create_engine()
    edit = engine.create_edit()
    track = edit.insert_audio_track("Bass")
    del edit
    gc.collect()

    assert track.get_name() == "Bass"
    track.set_volume(0.5)
    track.set_pan(-0.2)
    track.set_mute(True)


# ---------------------------------------------------------------------------
# keep_alive: Track stays alive while Clip/Plugin exist
# ---------------------------------------------------------------------------

def test_clip_survives_track_variable_deletion():
    """del track should NOT destroy Track while a Clip holds keep_alive ref."""
    engine = dawsmith.create_engine()
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_midi_clip("MyClip", 0.0, 4.0)
    del track
    gc.collect()

    assert clip.get_name() == "MyClip"
    clip.add_note(60, 0.0, 1.0)
    clip.clear_notes()
    clip.add_note(72, 0.0, 2.0, velocity=80)


def test_plugin_survives_track_variable_deletion(engine_with_plugins,
                                                  first_instrument):
    """del track should NOT destroy Track while a Plugin holds keep_alive ref."""
    edit = engine_with_plugins.create_edit()
    track = edit.insert_audio_track("Synth")
    plugin = track.insert_plugin(first_instrument.identifier)
    del track
    gc.collect()

    assert plugin.is_loaded()
    name = plugin.get_name()
    assert isinstance(name, str) and len(name) > 0
    count = plugin.get_parameter_count()
    assert count > 0


# ---------------------------------------------------------------------------
# Deep hierarchy: all variables deleted except leaf
# ---------------------------------------------------------------------------

def test_deep_hierarchy_leaf_keeps_ancestors_alive():
    """Deleting engine/edit/track variables should be safe if clip ref exists."""
    engine = dawsmith.create_engine()
    edit = engine.create_edit()
    track = edit.insert_audio_track("Deep")
    clip = track.insert_midi_clip("Leaf", 0.0, 8.0)

    del engine, edit, track
    gc.collect()

    assert clip.get_name() == "Leaf"
    clip.add_note(64, 0.0, 4.0, velocity=90)


# ---------------------------------------------------------------------------
# Create/destroy cycles
# ---------------------------------------------------------------------------

def test_create_destroy_edit_cycle():
    """Creating and destroying many edits should not leak or crash."""
    engine = dawsmith.create_engine()
    for i in range(50):
        edit = engine.create_edit(bpm=60.0 + i)
        track = edit.insert_audio_track(f"T{i}")
        clip = track.insert_midi_clip("C", 0.0, 4.0)
        clip.add_note(60, 0.0, 1.0)
        del clip, track, edit
    gc.collect()
    # Engine should still work
    final_edit = engine.create_edit()
    assert final_edit is not None


def test_create_destroy_multiple_engines():
    """Creating and destroying multiple engines should not crash."""
    for i in range(10):
        engine = dawsmith.create_engine()
        edit = engine.create_edit()
        edit.insert_audio_track(f"Track{i}")
        del edit, engine
    gc.collect()


# ---------------------------------------------------------------------------
# GC stress
# ---------------------------------------------------------------------------

def test_gc_stress_many_objects():
    """Create many objects and let GC sort out destruction order."""
    engine = dawsmith.create_engine()
    edits = []
    tracks = []
    clips = []

    for i in range(10):
        edit = engine.create_edit(bpm=100.0 + i)
        edits.append(edit)
        for j in range(3):
            track = edit.insert_audio_track(f"T{i}_{j}")
            tracks.append(track)
            clip = track.insert_midi_clip("C", 0.0, 4.0)
            clips.append(clip)
            clip.add_note(60 + j, 0.0, 1.0)

    # Delete in scrambled order
    del clips
    gc.collect()
    del engine
    gc.collect()
    del tracks
    gc.collect()
    del edits
    gc.collect()


def test_gc_implicit_cleanup():
    """Objects created in a function should be safely cleaned up on return."""
    def inner():
        engine = dawsmith.create_engine()
        edit = engine.create_edit()
        track = edit.insert_audio_track("Temp")
        clip = track.insert_midi_clip("C", 0.0, 4.0)
        clip.add_note(60, 0.0, 1.0)
        # All go out of scope here

    inner()
    gc.collect()
    # If we get here without segfault, the test passes.


# ---------------------------------------------------------------------------
# Exception types exist
# ---------------------------------------------------------------------------

def test_exception_types_importable():
    """EngineDestroyedError and ObjectDeletedError should be importable."""
    assert issubclass(dawsmith.EngineDestroyedError, RuntimeError)
    assert issubclass(dawsmith.ObjectDeletedError, RuntimeError)


# ---------------------------------------------------------------------------
# Conditional MessageManager pumping (play/stop)
# ---------------------------------------------------------------------------

def test_play_stop_state_transitions(engine_with_plugins, first_instrument):
    """play() and stop() should reliably transition transport state."""
    edit = engine_with_plugins.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Synth")
    track.insert_plugin(first_instrument.identifier)
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 4.0, velocity=100)

    assert not edit.is_playing()

    edit.play()
    assert edit.is_playing(), "Transport should be playing after play()"

    pos = edit.get_position_seconds()
    assert isinstance(pos, float)

    edit.stop()
    assert not edit.is_playing(), "Transport should be stopped after stop()"


def test_play_stop_cycle(engine_with_plugins, first_instrument):
    """Multiple play/stop cycles should work reliably."""
    edit = engine_with_plugins.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Synth")
    track.insert_plugin(first_instrument.identifier)
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 4.0, velocity=100)

    for _ in range(3):
        edit.play()
        assert edit.is_playing()
        edit.stop()
        assert not edit.is_playing()


# ---------------------------------------------------------------------------
# Render still works after lifetime changes
# ---------------------------------------------------------------------------

def test_render_after_engine_variable_deletion(engine_with_plugins,
                                                first_instrument, tmp_path):
    """Render should work even after the engine variable is deleted."""
    edit = engine_with_plugins.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Synth")
    track.insert_plugin(first_instrument.identifier)
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 4.0, velocity=100)

    # NOTE: We cannot del engine_with_plugins since it's a session fixture.
    # Instead, test that render works through the normal keep_alive path.
    wav_path = str(tmp_path / "lifetime_render.wav")
    opts = dawsmith.RenderOptions()
    opts.output_path = wav_path
    opts.sample_rate = 44100
    opts.bit_depth = 16
    opts.end_seconds = 2.0
    edit.render(opts)

    import os
    assert os.path.isfile(wav_path)
    assert os.path.getsize(wav_path) > 100
