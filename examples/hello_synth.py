"""DAWsmith demo: MIDI chord through Dexed VST3 -> WAV file."""

import dawsmith
import os
import sys

def main():
    engine = dawsmith.create_engine()

    # Scan local vsts/ folder
    vst_path = os.path.join(os.path.dirname(__file__), "..", "vsts")
    if not os.path.isdir(vst_path):
        print(f"VST directory not found: {vst_path}")
        print("Download Dexed and extract to vsts/")
        sys.exit(1)

    print(f"Scanning {vst_path}...")
    engine.scan_plugins(vst_path)

    plugins = engine.get_available_plugins()
    print(f"Found {len(plugins)} plugin(s):")
    for p in plugins:
        kind = "instrument" if p.is_instrument else "effect"
        print(f"  [{kind}] {p.name} ({p.manufacturer}) - {p.format}")

    instruments = [p for p in plugins if p.is_instrument]
    if not instruments:
        print("\nNo instrument plugins found.")
        sys.exit(1)

    synth = instruments[0]
    print(f"\nUsing: {synth.name}")

    # Create project
    edit = engine.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Synth")
    plugin = track.insert_plugin(synth.identifier)
    print(f"Plugin loaded: {plugin.get_name()} ({plugin.get_parameter_count()} params)")

    # Add a C major chord
    clip = track.insert_midi_clip("chord", start_beat=0.0, length_beats=4.0)
    clip.add_note(60, 0.0, 4.0, velocity=100)  # C4
    clip.add_note(64, 0.0, 4.0, velocity=90)   # E4
    clip.add_note(67, 0.0, 4.0, velocity=90)   # G4

    # Render to WAV
    output = "hello_synth.wav"
    opts = dawsmith.RenderOptions()
    opts.output_path = output
    opts.sample_rate = 44100
    opts.bit_depth = 16
    opts.end_seconds = 3.0

    print(f"\nRendering to {output}...")
    edit.render(opts)
    print(f"Done! Open {output} in any audio player.")

    # Explicit cleanup (edit must be destroyed before engine)
    del edit, engine


if __name__ == "__main__":
    main()
