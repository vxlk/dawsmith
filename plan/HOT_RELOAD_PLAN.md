# Hot Reload Implementation Plan

## Overview

Enable a live coding workflow for DAWsmith: write a Python script, hear it play, edit the script, hear changes immediately — without restarting. This is the programmatic equivalent of tweaking knobs in a DAW while the transport is rolling.

This replaces the "Built-in Plugins" item (1.2) in the development plan as a Phase 1 priority. Free VST3 instruments and effects (Dexed, OB-Xd, Vital, etc.) are plentiful; a live coding workflow is a differentiator.

---

## Goals

1. **REPL modification** — call `clip.add_note(...)`, `plugin.set_parameter_value(...)`, `edit.set_tempo(140)` while audio is playing, hear changes immediately
2. **File-watch hot reload** — save a `.py` file, changes are applied to the running playback automatically
3. **Live coding session** — a single entry point (`dawsmith.live("my_song.py")`) that manages engine, playback, file watching, and reload
4. **Loop mode** — loop a beat range continuously while iterating on content
5. **Everything that affects sound** — notes, clips, tracks, plugins, parameters, volume/pan/mute, tempo are all hot-reloadable

---

## Architecture Overview

```
                          User's Editor
                              |
                         saves .py file
                              |
                              v
  +-------------------------------------------------+
  |              Python: LiveSession                 |
  |                                                  |
  |  main loop:                                      |
  |    1. watcher.check()       -- detect file change|
  |    2. if changed: reload()  -- re-exec build()   |
  |    3. print position/status                      |
  |    4. sleep(poll_interval)                        |
  +-------------------------------------------------+
                                |
                          modify Edit
                                |
                                v
  +-------------------------------------------------+
  |          C++: Tracktion Engine Backend           |
  |                                                  |
  |  Internal pump thread keeps MessageManager alive |
  |  Audio thread reads from Edit ValueTree          |
  |  ValueTree changes propagate automatically       |
  +-------------------------------------------------+
              |
              v
         Audio Output
```

**Key insight:** Tracktion Engine's Edit is a live document backed by JUCE's ValueTree system. Modifications to the Edit (add/remove notes, change parameters, add tracks) propagate to the audio thread automatically. We don't need a special "apply changes" step — the backend's internal pump thread keeps the JUCE message loop running so ValueTree callbacks are processed continuously.

**Design principle:** The JUCE MessageManager pump is a Tracktion Engine implementation detail. It does not belong on the abstract `Engine` interface or in the Python API. The Tracktion backend manages its own message loop internally (via a background pump thread started at engine creation). Other future backends would have their own equivalent mechanisms — or none at all.

---

## Implementation Phases

### Phase A: C++ Foundation

New methods needed on the abstract interface (`dawsmith.h`) and Tracktion backend.

#### A1. Internal Message Loop Pump (Backend-Only)

The JUCE MessageManager must be pumped continuously for ValueTree changes to propagate to the audio thread. This is a Tracktion Engine implementation detail — it does **not** belong on the abstract `Engine` interface in `dawsmith.h`.

The `TracktionEngine` backend starts an internal pump thread on construction and stops it on destruction. This thread runs `runDispatchLoopUntil` in a loop, keeping the message loop alive for the entire lifetime of the engine.

```cpp
// tracktion_backend.h — private members
class TracktionEngine : public Engine {
    // ...existing...
private:
    void pump(int timeout_ms = 10);  // internal only, not on abstract interface
    std::thread pump_thread_;
    std::atomic<bool> pump_running_{false};
};
```

```cpp
// tracktion_backend.cpp
void TracktionEngine::pump(int timeout_ms) {
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(timeout_ms);
}

// Called from constructor after engine init:
void TracktionEngine::start_pump_thread() {
    pump_running_ = true;
    pump_thread_ = std::thread([this]() {
        while (pump_running_) {
            pump(10);
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    });
}

// Called from destructor:
void TracktionEngine::stop_pump_thread() {
    pump_running_ = false;
    if (pump_thread_.joinable())
        pump_thread_.join();
}
```

Refactor `play()`, `stop()`, `is_playing()`, `get_position_seconds()` to remove their inline `runDispatchLoopUntil` calls — the internal pump thread now handles this continuously.

**Important caveat:** JUCE's MessageManager has thread-affinity requirements — `runDispatchLoopUntil` must be called from the thread that created the MessageManager. In headless mode, this is whichever thread initialized JUCE. The pump thread must be the thread that creates the MessageManager, or we must verify that headless mode on Windows is lenient about this. See Open Questions.

#### A2. Looping Support

```cpp
// dawsmith.h — new methods on Edit
virtual void set_loop_range(double start_beat, double end_beat) = 0;
virtual void enable_looping(bool enabled) = 0;
virtual bool is_looping() const = 0;
```

```cpp
// tracktion_backend.cpp
void TracktionEdit::set_loop_range(double start_beat, double end_beat) {
    if (!edit_) return;
    auto& transport = edit_->getTransport();
    auto& tempo = edit_->tempoSequence;
    auto start_time = tempo.beatsToTime(te::BeatPosition::fromBeats(start_beat));
    auto end_time = tempo.beatsToTime(te::BeatPosition::fromBeats(end_beat));
    transport.setLoopRange(te::TimeRange(start_time, end_time));
}

void TracktionEdit::enable_looping(bool enabled) {
    if (!edit_) return;
    edit_->getTransport().looping.setValue(enabled, nullptr);
}

bool TracktionEdit::is_looping() const {
    if (!edit_) return false;
    return edit_->getTransport().looping.get();
}
```

#### A3. Edit Content Clearing

For hot reload, we need to clear the Edit's content and rebuild. Two levels:

```cpp
// dawsmith.h — new methods
class Edit {
    // ...existing...
    virtual void clear_all_tracks() = 0;    // remove all audio tracks
    virtual int get_track_count() const = 0; // introspection
};

class Track {
    // ...existing...
    virtual void clear_clips() = 0;    // remove all MIDI clips from track
    virtual void clear_plugins() = 0;  // remove all user plugins from track
};
```

```cpp
// tracktion_backend.cpp
void TracktionEdit::clear_all_tracks() {
    if (!edit_) return;

    // Clear our wrappers first (releases references)
    tracks_.clear();

    // Remove actual Tracktion audio tracks from the Edit
    auto audioTracks = te::getAudioTracks(*edit_);
    for (int i = audioTracks.size() - 1; i >= 0; --i) {
        edit_->deleteTrack(audioTracks[i]);
    }
}

void TracktionTrack::clear_clips() {
    if (!track_) return;
    clips_.clear();  // clear our wrappers

    // Remove actual clips from the Tracktion track
    auto clips = track_->getClips();
    for (int i = clips.size() - 1; i >= 0; --i) {
        clips[i]->removeFromParentTrack();
    }
}

void TracktionTrack::clear_plugins() {
    if (!track_) return;
    plugins_.clear();  // clear our wrappers

    // Remove user plugins (skip built-in volume/pan plugin at index 0)
    auto& pluginList = track_->pluginList;
    for (int i = pluginList.size() - 1; i >= 0; --i) {
        auto* p = pluginList[i];
        if (dynamic_cast<te::VolumeAndPanPlugin*>(p) == nullptr)
            pluginList.removePlugin(p, false);
    }
}
```

**Thread safety note:** Tracktion Engine's ValueTree changes are dispatched to the audio thread via a lock-free queue. Removing tracks/clips while the transport is playing is safe — the audio thread will stop reading from removed nodes on its next process block (typically within 1-10ms at 44.1kHz with 256-512 sample buffer). During the rebuild window (clear -> repopulate), there will be a brief moment of silence, but the transport keeps running.

#### A4. `Edit::set_position(double seconds)`

Needed for resuming playback at the correct position after rebuild, and for general live session control.

```cpp
// dawsmith.h
virtual void set_position(double seconds) = 0;
```

```cpp
// tracktion_backend.cpp
void TracktionEdit::set_position(double seconds) {
    if (!edit_) return;
    edit_->getTransport().setPosition(te::TimePosition::fromSeconds(seconds));
}
```

#### A5. Python Bindings

Add new methods to `python_bindings.cpp`. Note: `pump()` is **not** exposed — it is internal to the Tracktion backend.

```cpp
// Edit
.def("set_loop_range", &Edit::set_loop_range,
     nb::arg("start_beat"), nb::arg("end_beat"))
.def("enable_looping", &Edit::enable_looping, nb::arg("enabled"))
.def("is_looping", &Edit::is_looping)
.def("clear_all_tracks", &Edit::clear_all_tracks)
.def("get_track_count", &Edit::get_track_count)
.def("set_position", &Edit::set_position, nb::arg("seconds"))

// Track
.def("clear_clips", &Track::clear_clips)
.def("clear_plugins", &Track::clear_plugins)
```

---

### Phase B: Python LiveSession Core

The `LiveSession` class manages the engine, edit, file watcher, and main event loop.

#### B1. LiveSession Class

```python
# src/dawsmith/live.py

import importlib.util
import os
import sys
import time
import traceback

from dawsmith import create_engine


class LiveSession:
    """Manages a live coding session with hot reload."""

    def __init__(self, script_path, *, vst_path=None, bpm=120.0,
                 loop_range=None, poll_interval=0.5):
        self.script_path = os.path.abspath(script_path)
        self.vst_path = vst_path
        self.bpm = bpm
        self.loop_range = loop_range          # (start_beat, end_beat) or None
        self.poll_interval = poll_interval     # seconds between file checks
        self.engine = None
        self.edit = None
        self._running = False
        self._last_mtime = 0.0
        self._last_error = None

    def start(self):
        """Initialize engine, load script, start playback, enter main loop."""
        self.engine = create_engine()

        if self.vst_path:
            print(f"Scanning plugins: {self.vst_path}")
            self.engine.scan_plugins(self.vst_path)

        self.edit = self.engine.create_edit(self.bpm)

        # Initial build
        if not self._load_and_build():
            print("Fix errors in your script and save. Waiting...")

        # Set up looping
        if self.loop_range:
            self.edit.set_loop_range(*self.loop_range)
            self.edit.enable_looping(True)

        # Start playback
        self.edit.play()
        self._running = True

        print(f"Live session started: {os.path.basename(self.script_path)}")
        if self.loop_range:
            print(f"Looping: beats {self.loop_range[0]}-{self.loop_range[1]}")
        print("Watching for changes... (Ctrl+C to stop)\n")

        self._run_loop()

    def stop(self):
        """Stop playback and clean up."""
        self._running = False
        if self.edit:
            self.edit.stop()
        # Explicit cleanup for object lifetime safety
        del self.edit
        del self.engine
        self.edit = None
        self.engine = None

    def _run_loop(self):
        """Main event loop: watch for file changes, display status.

        The C++ backend's internal pump thread keeps the JUCE message
        loop alive — we don't need to pump from Python.
        """
        try:
            while self._running:
                # 1. Check for file changes
                if self._file_changed():
                    self._reload()

                # 2. Print position
                if self.edit.is_playing():
                    pos = self.edit.get_position_seconds()
                    status = " [ERROR]" if self._last_error else ""
                    print(f"\rPosition: {pos:.1f}s{status}    ",
                          end="", flush=True)

                # 3. Sleep until next poll
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n")
        finally:
            self.stop()
            print("Session ended.")

    def _file_changed(self):
        """Check if the script file has been modified."""
        try:
            mtime = os.path.getmtime(self.script_path)
            if mtime > self._last_mtime:
                self._last_mtime = mtime
                return True
        except OSError:
            pass
        return False

    def _load_and_build(self):
        """Import the user's script and call its build() function.

        Returns True on success, False on error.
        """
        try:
            spec = importlib.util.spec_from_file_location(
                "dawsmith_live_script", self.script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, 'build'):
                print("\nError: script must define a build(edit, engine) function")
                return False

            module.build(self.edit, self.engine)
            self._last_error = None
            return True

        except Exception:
            self._last_error = traceback.format_exc()
            print(f"\n--- Reload Error ---")
            print(self._last_error)
            print(f"--- Fix and save to retry ---\n")
            return False

    def _reload(self):
        """Hot-reload the script: clear edit, re-build, continue playing."""
        pos = self.edit.get_position_seconds()
        was_looping = self.edit.is_looping()
        loop_range = self.loop_range

        # Clear all content (transport keeps running)
        self.edit.clear_all_tracks()

        # Rebuild from script
        if self._load_and_build():
            print(f"\n--- Reloaded at {pos:.1f}s ---\n")
        # else: error printed by _load_and_build, edit is empty but
        # transport keeps running (silence). Next save will retry.

        # Restore loop state
        if was_looping and loop_range:
            self.edit.set_loop_range(*loop_range)
            self.edit.enable_looping(True)
```

#### B2. Entry Point Function

```python
# Added to src/dawsmith/__init__.py or src/dawsmith/live.py

def live(script_path, *, vst_path=None, bpm=120.0, loop=None):
    """Start a live coding session.

    Args:
        script_path: Path to a Python script with a build(edit, engine) function.
        vst_path: Path to VST3 plugin directory (optional).
        bpm: Initial tempo.
        loop: Tuple of (start_beat, end_beat) to loop, or None.

    The script's build() function will be called initially and again whenever
    the file is saved. The Edit is cleared before each rebuild.

    Example:
        dawsmith.live("my_song.py", vst_path="./vsts", loop=(0, 8))
    """
    session = LiveSession(script_path, vst_path=vst_path, bpm=bpm,
                          loop_range=loop)
    session.start()
```

#### B3. CLI Entry Point

```python
# src/dawsmith/__main__.py

"""CLI: python -m dawsmith live my_song.py [--vst-path ./vsts] [--bpm 120] [--loop 0 8]"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="dawsmith")
    sub = parser.add_subparsers(dest="command")

    live_parser = sub.add_parser("live", help="Start a live coding session")
    live_parser.add_argument("script", help="Path to build script")
    live_parser.add_argument("--vst-path", help="VST3 plugin directory")
    live_parser.add_argument("--bpm", type=float, default=120.0)
    live_parser.add_argument("--loop", nargs=2, type=float, metavar=("START", "END"),
                             help="Loop range in beats (e.g. --loop 0 8)")

    args = parser.parse_args()

    if args.command == "live":
        from dawsmith.live import LiveSession
        loop = tuple(args.loop) if args.loop else None
        session = LiveSession(args.script, vst_path=args.vst_path,
                              bpm=args.bpm, loop_range=loop)
        session.start()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### Phase C: User Script Convention

#### C1. The `build()` Function

User scripts must define a `build(edit, engine)` function. This function is called:
- Once on session start
- Again each time the file is saved (after clearing the Edit)

The function receives a clean Edit (no tracks) and should populate it fully.

```python
# Example: my_song.py

def build(edit, engine):
    """Called by LiveSession on start and each reload."""
    edit.set_tempo(140.0)

    # Lead synth
    lead = edit.insert_audio_track("Lead")
    lead.insert_plugin("Dexed")
    clip = lead.insert_midi_clip("melody", 0.0, 8.0)
    for i, pitch in enumerate([60, 62, 64, 65, 67, 69, 71, 72]):
        clip.add_note(pitch, start_beat=float(i), length_beats=0.9, velocity=100)

    # Bass
    bass = edit.insert_audio_track("Bass")
    bass.insert_plugin("Dexed")
    bass.set_volume(0.7)
    bass_clip = bass.insert_midi_clip("bassline", 0.0, 8.0)
    for i in range(8):
        bass_clip.add_note(36, start_beat=float(i), length_beats=0.5, velocity=90)
```

**Why a function, not top-level code?** Top-level code would need the Edit and Engine to exist as globals, which is fragile. A function receives them as arguments, is easy to re-call, and avoids import side effects.

#### C2. Advanced Pattern: Stateful Reload

For users who want to preserve state across reloads (e.g., a note sequence that builds up over time), the `build()` function can accept an optional `state` dict:

```python
# This is a stretch goal, not needed for v1.
# Included here to show the design is extensible.

def build(edit, engine, state=None):
    state = state or {}
    count = state.get("reload_count", 0) + 1
    state["reload_count"] = count

    edit.set_tempo(120.0)
    track = edit.insert_audio_track("Evolving")
    track.insert_plugin("Dexed")
    clip = track.insert_midi_clip("notes", 0.0, 8.0)

    # Add more notes each reload
    for i in range(min(count, 8)):
        clip.add_note(60 + i * 2, float(i), 0.9, 100)

    return state  # LiveSession stores and passes back next time
```

---

### Phase D: REPL Integration

Since the backend's internal pump thread keeps the JUCE message loop alive automatically, REPL modification works out of the box. No special setup is needed — the user just creates objects and modifies them.

#### D1. Direct Modification During Playback

```python
>>> import dawsmith
>>> engine = dawsmith.create_engine()
>>> engine.scan_plugins("./vsts")
>>> edit = engine.create_edit(120.0)
>>> track = edit.insert_audio_track("Synth")
>>> track.insert_plugin("Dexed")
>>> clip = track.insert_midi_clip("notes", 0.0, 8.0)
>>> clip.add_note(60, 0.0, 1.0, 100)
>>> edit.enable_looping(True)
>>> edit.set_loop_range(0.0, 8.0)
>>> edit.play()

# The backend pump thread keeps audio alive while the REPL waits for input:
>>> clip.add_note(64, 1.0, 1.0, 100)   # hear it on next loop
>>> clip.add_note(67, 2.0, 1.0, 100)   # hear it on next loop
>>> edit.set_tempo(140.0)                # tempo changes live
>>> track.set_volume(0.5)               # volume changes live
```

This "just works" because the internal C++ pump thread runs independently of the Python GIL. The REPL can block waiting for input while audio continues to play and ValueTree changes propagate.

#### D2. REPL Helper

A convenience function for REPL use:

```python
def repl(*, vst_path=None, bpm=120.0, loop=None):
    """Start an interactive session with live audio.

    Returns (engine, edit) for REPL manipulation.
    The backend's internal pump thread keeps audio alive automatically.
    """
    engine = create_engine()
    if vst_path:
        engine.scan_plugins(vst_path)
    edit = engine.create_edit(bpm)
    if loop:
        edit.set_loop_range(*loop)
        edit.enable_looping(True)

    return engine, edit
```

Usage:
```python
>>> engine, edit = dawsmith.repl(vst_path="./vsts", loop=(0, 8))
>>> track = edit.insert_audio_track("Synth")
>>> # ... build and modify live ...
>>> edit.play()
>>> # Changes are heard immediately
```

---

### Phase E: Seamless Reload (Stretch Goal)

The gapped approach (Phase B/C) clears all tracks then rebuilds. This creates a brief silence window during rebuild. For most scripts (< 100ms rebuild time), this is imperceptible. But for complex setups with many plugins, the gap may be audible.

#### E1. Measure the Gap First

Before implementing seamless reload, measure the actual gap:
- Simple scripts (1 track, 1 plugin, 1 clip): likely < 5ms rebuild
- Medium scripts (4 tracks, 4 plugins, 4 clips): likely < 50ms rebuild
- Complex scripts (10+ tracks, 10+ plugins): could be 100-500ms

If the gap is consistently < 20ms (one audio buffer at 48kHz/1024 samples), seamless reload is unnecessary.

#### E2. Double-Buffer Strategy (If Needed)

If the gap is perceptible:

1. **Build phase:** Execute `build()` creating new tracks alongside existing ones, with new tracks muted
2. **Swap phase:** In a single operation, unmute new tracks and mute old tracks
3. **Cleanup phase:** Remove old tracks

```python
def _reload_seamless(self):
    # 1. Build new content alongside old (new tracks are appended)
    old_track_count = self.edit.get_track_count()
    if not self._load_and_build():
        return  # error — keep old content

    # 2. Mute old tracks, unmute new tracks
    # (This requires track indexing — get_track(i) method needed)
    for i in range(old_track_count):
        self.edit.get_track(i).set_mute(True)

    # 3. Remove old tracks
    for i in range(old_track_count - 1, -1, -1):
        self.edit.remove_track(i)
```

This requires `Edit::get_track(int index)` and `Edit::remove_track(int index)` methods.

#### E3. Diff-and-Patch Strategy (Future)

The most sophisticated approach: compare old and new Edit state, apply minimal changes. This requires the `EditData` extraction API from Phase 2 of the main development plan. Defer until that infrastructure exists.

---

## Thread Safety Analysis

### Threading Model

```
Main Thread (Python)          Internal Pump Thread (C++)     Audio Thread
─────────────────────         ──────────────────────────     ────────────
  create_engine()  ────────>  pump thread starts
  create_edit()               pump(10ms) loop  ──────────>  audio callback
  insert_audio_track()          (runs continuously)
  add_note()
  play()  ─────────────────────────────────────────────────> transport starts
  ...
  # LiveSession:
  _run_loop():
    watcher.check()
    if changed: _reload()
      clear_all_tracks()  ─────────────────────────────────> stops reading
      build()                                                  cleared tracks
        insert_audio_track()  ─────────────────────────────> starts reading
        add_note()                                             new tracks
        insert_plugin()
    print position
    sleep(poll_interval)
  ...
  del engine  ─────────────>  pump thread stops
```

### Safety Guarantees

- **ValueTree thread safety:** Tracktion Engine uses a lock-free message queue to propagate ValueTree changes from the message thread to the audio thread. All modifications go through this queue.
- **Python GIL:** All Python-initiated modifications happen on the main thread while holding the GIL. The C++ pump thread does not hold the GIL, so it never contends with Python code on shared Python state.
- **Plugin instantiation:** Creating plugins may involve async initialization. The pump thread ensures callbacks are dispatched. Plugin audio processing starts on the audio thread once initialization completes.
- **Deletion during playback:** Tracktion Engine handles this safely — deleted objects are reference-counted (`Ptr` / `shared_ptr`), so the audio thread finishes its current block before the object is actually freed.

### Risk: JUCE MessageManager Thread Affinity

JUCE expects `runDispatchLoopUntil` to be called from the "message thread." In headless mode, the message thread is whichever thread created the MessageManager. Currently that's the main Python thread. If we pump from a different thread, JUCE may assert.

**Mitigation:**
1. Test on Windows first (our current platform). JUCE's Windows backend may be more lenient in headless mode.
2. If assertions fire, initialize the MessageManager on the pump thread instead of the main Python thread — since the pump thread is the one that needs to dispatch, it should be the "message thread."
3. As a last resort, pump from the main thread only. LiveSession would need to call an internal pump in its loop, and REPL use would require an async REPL or periodic manual action. This is the least desirable option.

---

## API Summary

### New C++ Abstract Interface Methods (dawsmith.h)

```cpp
class Edit {
    // ...existing...
    virtual void set_loop_range(double start_beat, double end_beat) = 0;
    virtual void enable_looping(bool enabled) = 0;
    virtual bool is_looping() const = 0;
    virtual void clear_all_tracks() = 0;
    virtual int get_track_count() const = 0;
    virtual void set_position(double seconds) = 0;
};

class Track {
    // ...existing...
    virtual void clear_clips() = 0;
    virtual void clear_plugins() = 0;
};
```

Note: `pump()` is **not** on the abstract interface. It is a private implementation detail of `TracktionEngine` (see A1).

### New C++ Backend-Only (tracktion_backend.h)

```cpp
class TracktionEngine : public Engine {
    // ...existing...
private:
    void pump(int timeout_ms = 10);
    void start_pump_thread();
    void stop_pump_thread();
    std::thread pump_thread_;
    std::atomic<bool> pump_running_{false};
};
```

### New Python API

```python
# Live coding session (file-watch mode)
dawsmith.live("my_song.py", vst_path="./vsts", bpm=120, loop=(0, 8))

# REPL mode
engine, edit = dawsmith.repl(vst_path="./vsts", loop=(0, 8))

# CLI
# python -m dawsmith live my_song.py --vst-path ./vsts --loop 0 8

# Direct methods (available on existing objects)
edit.set_loop_range(0.0, 8.0)
edit.enable_looping(True)
edit.is_looping()
edit.clear_all_tracks()
edit.get_track_count()
edit.set_position(2.5)
track.clear_clips()
track.clear_plugins()
```

---

## Error Handling

### Script Errors During Reload

When the user's script has a syntax error or runtime exception during hot reload:

1. Catch the exception in `_load_and_build()`
2. Print the full traceback to the console
3. **Keep the current (old) content playing** if possible — but with the clear-then-build approach, the Edit is already cleared. This means the user hears silence until they fix the error.
4. Print "Fix and save to retry" message
5. Continue watching for file changes

**Improvement for v2:** Use the double-buffer approach from Phase E — don't clear old content until the new build succeeds. This way, errors don't cause silence.

### Engine/JUCE Errors

- If the internal pump thread encounters an error, it logs and continues pumping
- If the audio device disconnects, Tracktion Engine handles reconnection internally
- If a plugin crashes during reload, catch at the `insert_plugin` level and report

### Ctrl+C Handling

The main loop catches `KeyboardInterrupt`, calls `stop()`, and cleans up. Signal handling in Python + JUCE can be tricky (JUCE installs its own signal handlers). Test this carefully.

---

## File Structure

```
src/
  dawsmith/
    __init__.py         # add: live(), repl() imports
    __main__.py         # NEW: CLI entry point
    live.py             # NEW: LiveSession class
  cpp/
    dawsmith.h          # MODIFIED: new methods on Engine, Edit, Track
    tracktion_backend.h # MODIFIED: new method declarations
    tracktion_backend.cpp  # MODIFIED: new method implementations
    python_bindings.cpp    # MODIFIED: bind new methods

examples/
    live_demo.py        # NEW: example live coding script with build()
```

---

## Example: `examples/live_demo.py`

```python
"""DAWsmith demo: live coding with hot reload.

Run with:
    python -m dawsmith live examples/live_demo.py --vst-path ./vsts --loop 0 8

Edit this file while it's running and save to hear changes.
"""


def build(edit, engine):
    edit.set_tempo(120.0)

    track = edit.insert_audio_track("Lead")

    instruments = [p for p in engine.get_available_plugins() if p.is_instrument]
    if instruments:
        track.insert_plugin(instruments[0].identifier)

    clip = track.insert_midi_clip("melody", 0.0, 8.0)

    # Try changing these notes and saving!
    melody = [60, 62, 64, 65, 67, 69, 71, 72]
    for i, pitch in enumerate(melody):
        clip.add_note(pitch, start_beat=float(i), length_beats=0.8, velocity=100)
```

---

## Testing Strategy

### Unit Tests (C++)

- `test_pump`: Call `pump(10)` — no crash, returns within timeout
- `test_loop_range`: Set loop range, verify `is_looping()` returns true
- `test_clear_all_tracks`: Insert 3 tracks, clear, verify `get_track_count() == 0`
- `test_clear_clips`: Insert clips, clear, verify track has no clips
- `test_clear_plugins`: Insert plugins, clear, verify only VolumeAndPan remains
- `test_set_position`: Set position, verify `get_position_seconds()` is near target

### Integration Tests (Python)

- `test_modify_during_playback`: Play, add note, verify no crash, stop
- `test_clear_and_rebuild_during_playback`: Play, clear, rebuild, verify playing continues
- `test_loop_mode`: Enable looping, play, verify position wraps around
- `test_live_session_reload`: Create LiveSession with a temp script, modify the script, verify rebuild happens
- `test_live_session_error_recovery`: Introduce syntax error in script, verify session continues, fix error, verify reload succeeds

### Manual Testing

- Run `live_demo.py` with a real VST3
- Edit notes while playing, verify audio changes
- Introduce a syntax error, verify error message and continued playback
- Fix the error, verify reload
- Test loop mode with different ranges
- Test tempo changes during playback

---

## Implementation Order

Priority-ordered list of tasks:

1. **Internal pump thread in `TracktionEngine`** — foundation, unlocks everything (A1)
2. **Looping support** — needed for iteration workflow (A2)
3. **`Edit::clear_all_tracks()`** — needed for reload (A3)
4. **`Edit::set_position()`** — needed for reload position restore (A4)
5. **`Track::clear_clips()`, `Track::clear_plugins()`** — fine-grained clearing (A3)
6. **Python bindings for new Edit/Track methods** (A5)
7. **`LiveSession` class** — core Python implementation (B1)
8. **`dawsmith.live()` entry point** (B2)
9. **CLI `python -m dawsmith live`** (B3)
10. **`dawsmith.repl()` helper** — REPL convenience (D2)
11. **Example `live_demo.py`** — documentation and demo
12. **Tests** — unit + integration
13. **Measure reload gap** — determine if seamless is needed (E1)
14. **Seamless reload** — only if gap is perceptible (E2)

Steps 1-9 are the core deliverable. Steps 10-12 are fast follow-ups. Steps 13-14 are stretch.

---

## Roadmap Integration

This plan replaces item **1.2 (Built-in Plugins)** in the development plan's Phase 1. The updated Phase 1 priority order becomes:

1. **Fix segfault** (object lifetime) — blocks everything
2. **Hot reload / live session** — this plan (differentiator feature)
3. **Cross-platform CI** — confidence in every change
4. **Audio clips + automation** — completes the core data model

Built-in plugins are deprioritized. Free VST3 plugins (Dexed, Vital, Surge XT, OB-Xd) cover the need. CI tests that need a synth without VST dependencies can use a simple sine-wave tone generator as a minimal fallback (a few lines of JUCE code, not a full built-in plugin system).

---

## Open Questions

1. **JUCE MessageManager thread affinity in headless mode** — the internal pump thread needs to call `runDispatchLoopUntil`, but JUCE expects this from the "message thread." Can the pump thread be the message thread if it creates the MessageManager? Needs testing on Windows. If thread affinity is strict and we can't work around it, the pump must happen on the main thread, which complicates REPL use.

2. **Plugin load time during rebuild** — VST3 plugin instantiation can take 50-500ms. If the same plugin is loaded every reload, can we cache the instance instead of re-creating it? Tracktion Engine's plugin cache may already handle this.

3. **Audio device reinitialization** — does clearing all tracks and rebuilding cause the audio device to reinitialize? It shouldn't (the device is owned by the Engine, not the Edit), but verify.

4. **Multiple Edits** — should LiveSession support multiple Edits (e.g., switching between songs)? Defer to v2.

5. **State preservation across reloads** — the `state` dict pattern (Phase C2) is shown but not implemented in the core LiveSession. Add if users request it.

6. **Windows terminal ANSI escape handling** — the `\r` position display assumes the terminal supports carriage return. Windows Terminal and modern PowerShell do; legacy cmd.exe may not. Test on target terminals.
