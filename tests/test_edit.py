import dawsmith
import pytest


def test_create_edit_default_bpm(engine):
    edit = engine.create_edit()
    assert edit is not None


def test_create_edit_custom_bpm(engine):
    edit = engine.create_edit(bpm=90.0)
    assert edit is not None


def test_insert_audio_track(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("Lead")
    assert track is not None
    assert track.get_name() == "Lead"


def test_insert_multiple_tracks(engine):
    edit = engine.create_edit()
    t1 = edit.insert_audio_track("Bass")
    t2 = edit.insert_audio_track("Drums")
    assert t1.get_name() == "Bass"
    assert t2.get_name() == "Drums"


def test_insert_midi_clip(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_midi_clip("MyClip", 0.0, 4.0)
    assert clip is not None
    assert clip.get_name() == "MyClip"


def test_add_notes_to_clip(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 1.0, velocity=100)
    clip.add_note(64, 1.0, 1.0, velocity=90)
    clip.add_note(67, 2.0, 1.0, velocity=80)


def test_clear_notes(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    clip = track.insert_midi_clip("C", 0.0, 4.0)
    clip.add_note(60, 0.0, 1.0)
    clip.clear_notes()
    clip.add_note(67, 0.0, 2.0)


def test_insert_plugin(engine_with_plugins, first_instrument):
    edit = engine_with_plugins.create_edit()
    track = edit.insert_audio_track("Synth")
    plugin = track.insert_plugin(first_instrument.identifier)
    assert plugin is not None
    assert plugin.is_loaded()


def test_plugin_has_name(engine_with_plugins, first_instrument):
    edit = engine_with_plugins.create_edit()
    track = edit.insert_audio_track("Synth")
    plugin = track.insert_plugin(first_instrument.identifier)
    name = plugin.get_name()
    assert isinstance(name, str) and len(name) > 0


def test_plugin_parameters(engine_with_plugins, first_instrument):
    edit = engine_with_plugins.create_edit()
    track = edit.insert_audio_track("Synth")
    plugin = track.insert_plugin(first_instrument.identifier)
    count = plugin.get_parameter_count()
    assert count > 0
    for i in range(min(count, 5)):
        name = plugin.get_parameter_name(i)
        assert isinstance(name, str)
        val = plugin.get_parameter_value(i)
        assert isinstance(val, float)


def test_set_volume_pan_mute(engine):
    edit = engine.create_edit()
    track = edit.insert_audio_track("T")
    track.set_volume(0.5)
    track.set_pan(-0.3)
    track.set_mute(True)
    track.set_mute(False)
