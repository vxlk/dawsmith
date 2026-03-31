"""DAWsmith demo: real-time playback through speakers."""

import dawsmith
import os
import sys
import time

def main():
    engine = dawsmith.create_engine()

    # Scan local vsts/ folder
    vst_path = os.path.join(os.path.dirname(__file__), "..", "vsts")
    if not os.path.isdir(vst_path):
        print(f"VST directory not found: {vst_path}")
        sys.exit(1)

    engine.scan_plugins(vst_path)

    instruments = [p for p in engine.get_available_plugins() if p.is_instrument]
    if not instruments:
        print("No instrument plugins found.")
        sys.exit(1)

    synth = instruments[0]
    print(f"Using: {synth.name}")

    # Build an arpeggio pattern
    edit = engine.create_edit(bpm=120.0)
    track = edit.insert_audio_track("Synth")
    track.insert_plugin(synth.identifier)

    clip = track.insert_midi_clip("arpeggio", start_beat=0.0, length_beats=16.0)
    pattern = [60, 64, 67, 72, 67, 64, 60, 55]
    for bar in range(2):
        for i, pitch in enumerate(pattern):
            beat = bar * 8 + i
            clip.add_note(pitch, start_beat=float(beat), length_beats=0.8,
                         velocity=100)

    # Play in real time
    print("Playing... (press Ctrl+C to stop)")
    edit.play()

    try:
        while edit.is_playing():
            pos = edit.get_position_seconds()
            print(f"\rPosition: {pos:.1f}s", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    edit.stop()
    print("\nStopped.")

    # Explicit cleanup (edit must be destroyed before engine)
    del edit, engine


if __name__ == "__main__":
    main()
