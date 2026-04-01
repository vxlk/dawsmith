# DAWsmith: Architecture Plan (C++ Interface with Swappable Backends)

## Overview

DAWsmith uses a C++ abstract interface as the contract between the Python layer and the audio engine backends. Each backend is a shared library (`.so`/`.dylib`/`.dll`) that implements this interface. Python wraps the interface once via nanobind. Backend selection happens at runtime via dynamic loading.

```
┌─────────────────────────────────────────────────────────┐
│  dawsmith-pro (Proprietary)                             │
│  Templates, eval loop, agent integration, cloud API     │
│  Pure Python — imports dawsmith                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  dawsmith (MIT License)                                 │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Python layer                                      │ │
│  │  validate.py, export/, mir.py, batch.py            │ │
│  │  Consumes EditData/TrackData structs from C++      │ │
│  └────────────────────────┬───────────────────────────┘ │
│  ┌────────────────────────▼───────────────────────────┐ │
│  │  nanobind wrapper (_native.pyd)                    │ │
│  │  Wraps dawsmith.h interface ONCE                   │ │
│  └────────────────────────┬───────────────────────────┘ │
│  ┌────────────────────────▼───────────────────────────┐ │
│  │  dawsmith.h / dawsmith_factory.h (C++ interface)   │ │
│  │  Abstract classes + plain data structs              │ │
│  │  MIT License                                       │ │
│  └──────┬──────────────────────────────┬──────────────┘ │
└─────────┼──────────────────────────────┼────────────────┘
          │                              │
          │  dlopen / LoadLibrary        │  dlopen / LoadLibrary
          │                              │
┌─────────▼──────────┐    ┌─────────────▼────────────┐
│ libdawsmith-        │    │ libdawsmith-core         │
│ tracktion.so        │    │ .so / .dylib / .dll      │
│                     │    │                          │
│ Tracktion Engine    │    │ Custom JUCE engine       │
│ + JUCE              │    │ + JUCE (commercial)      │
│                     │    │                          │
│ GPLv3               │    │ Proprietary              │
└─────────────────────┘    └──────────────────────────┘
```

---

## 1. License Structure

| Component | License | Contains | Rationale |
|---|---|---|---|
| `dawsmith.h` + data structs | MIT | C++ abstract interface, factory, plain data types | Must be MIT so both GPL and proprietary backends can link against it |
| `dawsmith` (Python package) | MIT | nanobind wrapper, validation, exporters, MIR, batch | Must be MIT so commercial users have no GPL exposure |
| `libdawsmith-tracktion` | GPLv3 | Tracktion Engine backend shared library | Tracktion Engine is GPL; this inherits GPL |
| `libdawsmith-core` | Proprietary | Custom JUCE backend shared library | Built on JUCE commercial license; fully proprietary |
| `dawsmith-pro` | Proprietary | Intelligence layer (Python) | Templates, eval loop, agent, cloud API |

**Commercial customer stack**: MIT + Proprietary + Proprietary. No GPL.
**Open-source user stack**: MIT + GPLv3. Standard open-source terms.

The MIT interface is the keystone. Both backends link against it. Neither backend's license infects the interface or the Python layer because the interface is independently licensed and the backends are loaded at runtime via `dlopen`, not statically linked into the Python package.

---

## 2. C++ Interface Definition

### 2.1 Core Interface Header

```cpp
// dawsmith.h — MIT License
// This file defines the abstract interface that all backends implement.
// It contains NO implementation code, NO backend-specific includes.

#pragma once
#include <string>
#include <vector>
#include <memory>
#include <cstdint>

namespace dawsmith {

// ============================================================================
// Forward declarations
// ============================================================================
class Engine;
class Edit;
class Track;
class MidiClip;
class AudioClip;
class Plugin;
class AutomationCurve;

// ============================================================================
// Plain data structs — used for serialization, export, metadata
// These cross the C++/Python boundary as value types.
// No virtual methods, no pointers to backend objects.
// ============================================================================

struct MidiNoteData {
    int pitch;              // 0-127
    double start_beat;
    double length_beats;
    int velocity;           // 0-127
    int channel;            // 0-15
};

struct AutomationPointData {
    double beat;
    double value;           // normalized 0.0-1.0
    double curve;           // 0.0 = linear, negative = logarithmic, positive = exponential
};

struct PluginData {
    std::string name;
    std::string format;     // "VST3", "AU", "CLAP", "builtin"
    std::string identifier; // plugin ID or path
    std::vector<std::pair<std::string, double>> parameters;  // name → value
};

struct ClipData {
    std::string name;
    std::string type;       // "midi" or "audio"
    double start_beat;
    double length_beats;

    // MIDI clip data
    std::vector<MidiNoteData> notes;

    // Audio clip data
    std::string audio_file_path;
    double gain_db;
    bool looping;
};

struct AutomationLaneData {
    std::string parameter_name;
    std::string plugin_name;
    std::vector<AutomationPointData> points;
};

struct TrackData {
    std::string name;
    double volume;          // linear, 0.0-2.0 (1.0 = unity)
    double pan;             // -1.0 (left) to 1.0 (right)
    bool muted;
    bool soloed;
    std::vector<ClipData> clips;
    std::vector<PluginData> plugins;
    std::vector<AutomationLaneData> automation;
    std::vector<TrackData> child_tracks;  // for folder/submix tracks
};

struct TempoPointData {
    double beat;
    double bpm;
};

struct TimeSignatureData {
    double beat;
    int numerator;
    int denominator;
};

struct EditData {
    std::vector<TempoPointData> tempo_map;
    std::vector<TimeSignatureData> time_signatures;
    std::vector<TrackData> tracks;
    TrackData master_track;
    double duration_beats;
    double duration_seconds;
};

// ============================================================================
// Capabilities — what this backend supports
// ============================================================================

struct Capabilities {
    std::string backend_name;   // "tracktion" or "core"
    std::string backend_version;
    bool vst3;
    bool au;
    bool clap;
    bool audio_clips;
    bool midi_clips;
    bool automation;
    bool tempo_map;
    bool time_stretch;
    bool pdc;
    bool multithreaded_render;
    bool stem_export;
    bool clip_launcher;
    bool recording;
    bool realtime_playback;
};

// ============================================================================
// Render options
// ============================================================================

struct RenderOptions {
    std::string output_path;
    int sample_rate = 44100;
    int bit_depth = 24;
    int channels = 2;
    double start_beat = 0.0;
    double end_beat = -1.0;    // -1 = render to end of last clip
};

// ============================================================================
// Plugin description (from scan results)
// ============================================================================

struct PluginDescription {
    std::string name;
    std::string manufacturer;
    std::string identifier;     // unique ID
    std::string format;         // "VST3", "AU", "CLAP"
    std::string path;           // filesystem path
    bool is_instrument;
    int num_inputs;
    int num_outputs;
};

// ============================================================================
// Abstract interfaces — backends implement these
// ============================================================================

class AutomationCurve {
public:
    virtual ~AutomationCurve() = default;
    virtual void add_point(double beat, double value, double curve = 0.0) = 0;
    virtual void clear() = 0;
    virtual std::vector<AutomationPointData> get_points() = 0;
};

class Plugin {
public:
    virtual ~Plugin() = default;
    virtual std::string get_name() = 0;
    virtual std::vector<std::pair<std::string, double>> get_parameters() = 0;
    virtual void set_parameter(const std::string& name, double value) = 0;
    virtual double get_parameter(const std::string& name) = 0;
    virtual AutomationCurve* get_automation(const std::string& parameter_name) = 0;
    virtual void set_bypass(bool bypassed) = 0;
    virtual PluginData to_data() = 0;
};

class MidiClip {
public:
    virtual ~MidiClip() = default;
    virtual void add_note(int pitch, double start_beat, double length_beats,
                         int velocity = 100, int channel = 0) = 0;
    virtual void add_notes(const std::vector<MidiNoteData>& notes) = 0;
    virtual void clear_notes() = 0;
    virtual std::vector<MidiNoteData> get_notes() = 0;
    virtual void quantize(double grid_beats, double strength = 1.0) = 0;
    virtual std::string get_name() = 0;
    virtual double get_start_beat() = 0;
    virtual double get_length_beats() = 0;
    virtual ClipData to_data() = 0;
};

class AudioClip {
public:
    virtual ~AudioClip() = default;
    virtual void set_source(const std::string& file_path) = 0;
    virtual void set_gain_db(double gain) = 0;
    virtual void set_looping(bool loop) = 0;
    virtual std::string get_name() = 0;
    virtual double get_start_beat() = 0;
    virtual double get_length_beats() = 0;
    virtual ClipData to_data() = 0;
};

class Track {
public:
    virtual ~Track() = default;
    virtual std::string get_name() = 0;
    virtual void set_name(const std::string& name) = 0;

    virtual MidiClip* insert_midi_clip(const std::string& name,
                                       double start_beat,
                                       double length_beats) = 0;
    virtual AudioClip* insert_audio_clip(const std::string& name,
                                         const std::string& audio_path,
                                         double start_beat,
                                         double length_beats) = 0;

    virtual Plugin* insert_plugin(const std::string& identifier) = 0;
    virtual std::vector<Plugin*> get_plugins() = 0;
    virtual void remove_plugin(int index) = 0;

    virtual void set_volume(double linear) = 0;   // 0.0 - 2.0
    virtual void set_pan(double pan) = 0;          // -1.0 to 1.0
    virtual void set_mute(bool muted) = 0;
    virtual void set_solo(bool soloed) = 0;
    virtual double get_volume() = 0;
    virtual double get_pan() = 0;

    virtual TrackData to_data() = 0;
};

class Edit {
public:
    virtual ~Edit() = default;

    virtual Track* insert_audio_track(const std::string& name) = 0;
    virtual Track* insert_folder_track(const std::string& name) = 0;
    virtual std::vector<Track*> get_tracks() = 0;
    virtual Track* get_master_track() = 0;

    virtual void set_tempo(double bpm, double beat = 0.0) = 0;
    virtual void set_time_signature(int numerator, int denominator,
                                    double beat = 0.0) = 0;
    virtual double get_tempo_at_beat(double beat) = 0;
    virtual double get_duration_beats() = 0;
    virtual double get_duration_seconds() = 0;

    virtual void render(const RenderOptions& options) = 0;
    virtual std::map<std::string, std::string>
        render_stems(const std::string& output_dir, const RenderOptions& options) = 0;

    virtual EditData to_data() = 0;

    virtual void save(const std::string& path) = 0;
};

class Engine {
public:
    virtual ~Engine() = default;
    virtual std::unique_ptr<Edit> create_edit(int sample_rate = 44100,
                                              double bpm = 120.0) = 0;
    virtual Capabilities get_capabilities() = 0;
    virtual std::vector<PluginDescription> scan_plugins(
        const std::vector<std::string>& paths) = 0;
    virtual void shutdown() = 0;
};

}  // namespace dawsmith
```

### 2.2 Factory Header

```cpp
// dawsmith_factory.h — MIT License
#pragma once
#include "dawsmith.h"

namespace dawsmith {

enum class Backend {
    Auto,       // try Core first, fall back to Tracktion
    Tracktion,  // explicitly use GPL backend
    Core        // explicitly use proprietary backend
};

// Create an engine using the specified backend.
// Throws std::runtime_error if the backend is not available.
std::unique_ptr<Engine> create_engine(Backend backend = Backend::Auto);

// Query which backends are available on this system.
struct BackendAvailability {
    bool tracktion;
    bool core;
};
BackendAvailability get_available_backends();

}  // namespace dawsmith
```

### 2.3 Factory Implementation

```cpp
// dawsmith_factory.cpp — MIT License
#include "dawsmith_factory.h"

#ifdef _WIN32
    #include <windows.h>
    #define DAWSMITH_DLOPEN(path) LoadLibraryA(path)
    #define DAWSMITH_DLSYM(handle, name) GetProcAddress((HMODULE)handle, name)
    #define DAWSMITH_DLCLOSE(handle) FreeLibrary((HMODULE)handle)
    static const char* TRACKTION_LIB = "dawsmith_tracktion.dll";
    static const char* CORE_LIB = "dawsmith_core.dll";
#elif __APPLE__
    #include <dlfcn.h>
    #define DAWSMITH_DLOPEN(path) dlopen(path, RTLD_LAZY)
    #define DAWSMITH_DLSYM(handle, name) dlsym(handle, name)
    #define DAWSMITH_DLCLOSE(handle) dlclose(handle)
    static const char* TRACKTION_LIB = "libdawsmith_tracktion.dylib";
    static const char* CORE_LIB = "libdawsmith_core.dylib";
#else
    #include <dlfcn.h>
    #define DAWSMITH_DLOPEN(path) dlopen(path, RTLD_LAZY)
    #define DAWSMITH_DLSYM(handle, name) dlsym(handle, name)
    #define DAWSMITH_DLCLOSE(handle) dlclose(handle)
    static const char* TRACKTION_LIB = "libdawsmith_tracktion.so";
    static const char* CORE_LIB = "libdawsmith_core.so";
#endif

namespace dawsmith {

using CreateEngineFn = Engine* (*)();

static std::unique_ptr<Engine> try_load_backend(const char* lib_path) {
    void* handle = DAWSMITH_DLOPEN(lib_path);
    if (!handle) return nullptr;

    auto create_fn = (CreateEngineFn)DAWSMITH_DLSYM(handle, "dawsmith_create_engine");
    if (!create_fn) {
        DAWSMITH_DLCLOSE(handle);
        return nullptr;
    }

    // The backend owns the Engine; we wrap it in unique_ptr
    return std::unique_ptr<Engine>(create_fn());
}

std::unique_ptr<Engine> create_engine(Backend backend) {
    switch (backend) {
        case Backend::Core: {
            auto e = try_load_backend(CORE_LIB);
            if (!e) throw std::runtime_error("dawsmith-core backend not found");
            return e;
        }
        case Backend::Tracktion: {
            auto e = try_load_backend(TRACKTION_LIB);
            if (!e) throw std::runtime_error("dawsmith-tracktion backend not found");
            return e;
        }
        case Backend::Auto:
        default: {
            if (auto e = try_load_backend(CORE_LIB)) return e;
            if (auto e = try_load_backend(TRACKTION_LIB)) return e;
            throw std::runtime_error(
                "No DAWsmith backend found. Install either:\n"
                "  dawsmith-tracktion (open source, GPLv3)\n"
                "  dawsmith-core (commercial, requires license)\n"
            );
        }
    }
}

BackendAvailability get_available_backends() {
    BackendAvailability avail;
    void* h;

    h = DAWSMITH_DLOPEN(TRACKTION_LIB);
    avail.tracktion = (h != nullptr);
    if (h) DAWSMITH_DLCLOSE(h);

    h = DAWSMITH_DLOPEN(CORE_LIB);
    avail.core = (h != nullptr);
    if (h) DAWSMITH_DLCLOSE(h);

    return avail;
}

}  // namespace dawsmith
```

### 2.4 Backend Export Contract

Each backend shared library exports a single C function:

```cpp
// Every backend .so/.dylib/.dll must export this symbol:
extern "C" dawsmith::Engine* dawsmith_create_engine();
```

Tracktion backend:
```cpp
// tracktion_backend.cpp (in libdawsmith-tracktion)
#include "dawsmith.h"
#include "tracktion_engine_wrapper.h"

extern "C" dawsmith::Engine* dawsmith_create_engine() {
    return new TracktionEngineBackend();
}
```

Core backend:
```cpp
// core_backend.cpp (in libdawsmith-core)
#include "dawsmith.h"
#include "core_engine.h"

extern "C" dawsmith::Engine* dawsmith_create_engine() {
    return new CoreEngineBackend();
}
```

---

## 3. nanobind Wrapper (Written Once)

The nanobind module wraps `dawsmith.h` — the abstract interface. It has zero knowledge of either backend. It's compiled once and shipped with the `dawsmith` Python package.

```cpp
// python_bindings.cpp — MIT License
// Wraps dawsmith.h abstract interface. Does NOT include any backend headers.

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/map.h>
#include <nanobind/stl/unique_ptr.h>
#include "dawsmith.h"
#include "dawsmith_factory.h"

namespace nb = nanobind;
using namespace dawsmith;

NB_MODULE(_native, m) {
    m.doc() = "DAWsmith native bindings";

    // Enums
    nb::enum_<Backend>(m, "Backend")
        .value("Auto", Backend::Auto)
        .value("Tracktion", Backend::Tracktion)
        .value("Core", Backend::Core);

    // Data structs (value types, copied to/from Python)
    nb::class_<MidiNoteData>(m, "MidiNoteData")
        .def(nb::init<>())
        .def_rw("pitch", &MidiNoteData::pitch)
        .def_rw("start_beat", &MidiNoteData::start_beat)
        .def_rw("length_beats", &MidiNoteData::length_beats)
        .def_rw("velocity", &MidiNoteData::velocity)
        .def_rw("channel", &MidiNoteData::channel);

    nb::class_<Capabilities>(m, "Capabilities")
        .def_ro("backend_name", &Capabilities::backend_name)
        .def_ro("backend_version", &Capabilities::backend_version)
        .def_ro("vst3", &Capabilities::vst3)
        .def_ro("au", &Capabilities::au)
        .def_ro("clap", &Capabilities::clap)
        .def_ro("audio_clips", &Capabilities::audio_clips)
        .def_ro("midi_clips", &Capabilities::midi_clips)
        .def_ro("automation", &Capabilities::automation)
        .def_ro("tempo_map", &Capabilities::tempo_map)
        .def_ro("time_stretch", &Capabilities::time_stretch)
        .def_ro("pdc", &Capabilities::pdc)
        .def_ro("multithreaded_render", &Capabilities::multithreaded_render)
        .def_ro("stem_export", &Capabilities::stem_export);

    nb::class_<RenderOptions>(m, "RenderOptions")
        .def(nb::init<>())
        .def_rw("output_path", &RenderOptions::output_path)
        .def_rw("sample_rate", &RenderOptions::sample_rate)
        .def_rw("bit_depth", &RenderOptions::bit_depth)
        .def_rw("channels", &RenderOptions::channels)
        .def_rw("start_beat", &RenderOptions::start_beat)
        .def_rw("end_beat", &RenderOptions::end_beat);

    // EditData and sub-structs (for export layer)
    nb::class_<TrackData>(m, "TrackData")
        .def_ro("name", &TrackData::name)
        .def_ro("volume", &TrackData::volume)
        .def_ro("pan", &TrackData::pan)
        .def_ro("muted", &TrackData::muted)
        .def_ro("soloed", &TrackData::soloed)
        .def_ro("clips", &TrackData::clips)
        .def_ro("plugins", &TrackData::plugins)
        .def_ro("automation", &TrackData::automation)
        .def_ro("child_tracks", &TrackData::child_tracks);

    nb::class_<EditData>(m, "EditData")
        .def_ro("tempo_map", &EditData::tempo_map)
        .def_ro("time_signatures", &EditData::time_signatures)
        .def_ro("tracks", &EditData::tracks)
        .def_ro("master_track", &EditData::master_track)
        .def_ro("duration_beats", &EditData::duration_beats)
        .def_ro("duration_seconds", &EditData::duration_seconds);

    // Abstract interfaces (pointers managed by backend)
    nb::class_<AutomationCurve>(m, "AutomationCurve")
        .def("add_point", &AutomationCurve::add_point,
             nb::arg("beat"), nb::arg("value"), nb::arg("curve") = 0.0)
        .def("clear", &AutomationCurve::clear)
        .def("get_points", &AutomationCurve::get_points);

    nb::class_<Plugin>(m, "Plugin")
        .def("get_name", &Plugin::get_name)
        .def("get_parameters", &Plugin::get_parameters)
        .def("set_parameter", &Plugin::set_parameter)
        .def("get_parameter", &Plugin::get_parameter)
        .def("get_automation", &Plugin::get_automation, nb::rv_policy::reference)
        .def("set_bypass", &Plugin::set_bypass)
        .def("to_data", &Plugin::to_data);

    nb::class_<MidiClip>(m, "MidiClip")
        .def("add_note", &MidiClip::add_note,
             nb::arg("pitch"), nb::arg("start_beat"), nb::arg("length_beats"),
             nb::arg("velocity") = 100, nb::arg("channel") = 0)
        .def("add_notes", &MidiClip::add_notes)
        .def("clear_notes", &MidiClip::clear_notes)
        .def("get_notes", &MidiClip::get_notes)
        .def("quantize", &MidiClip::quantize,
             nb::arg("grid_beats"), nb::arg("strength") = 1.0)
        .def("get_name", &MidiClip::get_name)
        .def("to_data", &MidiClip::to_data);

    nb::class_<AudioClip>(m, "AudioClip")
        .def("set_source", &AudioClip::set_source)
        .def("set_gain_db", &AudioClip::set_gain_db)
        .def("set_looping", &AudioClip::set_looping)
        .def("get_name", &AudioClip::get_name)
        .def("to_data", &AudioClip::to_data);

    nb::class_<Track>(m, "Track")
        .def("get_name", &Track::get_name)
        .def("set_name", &Track::set_name)
        .def("insert_midi_clip", &Track::insert_midi_clip, nb::rv_policy::reference)
        .def("insert_audio_clip", &Track::insert_audio_clip, nb::rv_policy::reference)
        .def("insert_plugin", &Track::insert_plugin, nb::rv_policy::reference)
        .def("get_plugins", &Track::get_plugins)
        .def("remove_plugin", &Track::remove_plugin)
        .def("set_volume", &Track::set_volume)
        .def("set_pan", &Track::set_pan)
        .def("set_mute", &Track::set_mute)
        .def("set_solo", &Track::set_solo)
        .def("get_volume", &Track::get_volume)
        .def("get_pan", &Track::get_pan)
        .def("to_data", &Track::to_data);

    nb::class_<Edit>(m, "Edit")
        .def("insert_audio_track", &Edit::insert_audio_track, nb::rv_policy::reference)
        .def("insert_folder_track", &Edit::insert_folder_track, nb::rv_policy::reference)
        .def("get_tracks", &Edit::get_tracks)
        .def("get_master_track", &Edit::get_master_track, nb::rv_policy::reference)
        .def("set_tempo", &Edit::set_tempo,
             nb::arg("bpm"), nb::arg("beat") = 0.0)
        .def("set_time_signature", &Edit::set_time_signature,
             nb::arg("numerator"), nb::arg("denominator"), nb::arg("beat") = 0.0)
        .def("get_tempo_at_beat", &Edit::get_tempo_at_beat)
        .def("get_duration_beats", &Edit::get_duration_beats)
        .def("get_duration_seconds", &Edit::get_duration_seconds)
        .def("render", &Edit::render)
        .def("render_stems", &Edit::render_stems)
        .def("to_data", &Edit::to_data)
        .def("save", &Edit::save);

    nb::class_<Engine>(m, "Engine")
        .def("create_edit", &Engine::create_edit,
             nb::arg("sample_rate") = 44100, nb::arg("bpm") = 120.0)
        .def("get_capabilities", &Engine::get_capabilities)
        .def("scan_plugins", &Engine::scan_plugins)
        .def("shutdown", &Engine::shutdown);

    // Factory function
    m.def("create_engine", &create_engine,
          nb::arg("backend") = Backend::Auto,
          "Create a DAWsmith engine using the specified backend.");

    m.def("get_available_backends", &get_available_backends,
          "Query which backends are installed on this system.");
}
```

---

## 4. Python Package Structure

```
dawsmith/                              # MIT License — the single PyPI package
├── src/
│   ├── cpp/
│   │   ├── dawsmith.h                 # C++ abstract interface
│   │   ├── dawsmith_factory.h         # Backend loader
│   │   ├── dawsmith_factory.cpp       # dlopen logic
│   │   └── python_bindings.cpp        # nanobind (wraps dawsmith.h once)
│   │
│   └── dawsmith/                      # Python package
│       ├── __init__.py                # Public API, convenience wrappers
│       ├── engine.py                  # Pythonic wrapper around _native.Engine
│       ├── edit.py                    # Pythonic wrapper around _native.Edit
│       ├── track.py                   # Pythonic wrapper around _native.Track
│       ├── clip.py                    # Pythonic wrappers for clips
│       ├── plugin.py                  # Pythonic wrapper for plugins
│       │
│       ├── validate.py                # Validation suite (pure Python, uses librosa)
│       ├── mir.py                     # MIR utilities (pure Python, uses librosa)
│       │
│       ├── export/                    # Format exporters (pure Python)
│       │   ├── __init__.py
│       │   ├── dawproject.py          # Consumes EditData → .dawproject
│       │   ├── reaper.py             # Consumes EditData → .rpp
│       │   ├── ableton.py            # Consumes EditData → .als
│       │   ├── flstudio.py           # Consumes EditData → .flp
│       │   ├── midi.py               # Consumes EditData → .mid
│       │   └── metadata.py           # Consumes EditData → .json/.parquet
│       │
│       └── batch.py                   # Parallel batch runner (pure Python)
│
├── tests/                             # Shared test suite (runs against ANY backend)
│   ├── conftest.py                    # Backend discovery + parameterized fixtures
│   ├── test_lifecycle.py              # Engine/Edit create/destroy
│   ├── test_data_model.py             # Track/clip/plugin construction
│   ├── test_render.py                 # Audio render correctness
│   ├── test_midi.py                   # MIDI rendering
│   ├── test_mixing.py                 # Volume/pan/mute/solo/stems
│   ├── test_automation.py             # Automation curves
│   ├── test_plugins.py                # Plugin hosting
│   ├── test_determinism.py            # Reproducibility
│   ├── test_export_dawproject.py      # DAWproject validation
│   ├── test_export_reaper.py          # RPP validation
│   ├── test_export_midi.py            # MIDI validation
│   ├── test_export_metadata.py        # Metadata validation
│   ├── test_cross_format.py           # Cross-format consistency
│   ├── test_cross_backend.py          # Both backends produce equivalent results
│   ├── test_validation_suite.py       # Validator unit tests
│   └── golden/                        # Reference files
│
├── examples/
│   ├── hello_world.py
│   ├── multi_track.py
│   ├── export_all_formats.py
│   └── batch_generate.py
│
├── CMakeLists.txt                     # Builds: nanobind module (links dawsmith.h)
├── pyproject.toml
├── LICENSE                            # MIT
└── README.md
```

### 4.1 Pythonic Wrapper Layer

The raw nanobind bindings expose C++ semantics directly. A thin Python wrapper layer adds Pythonic conveniences:

```python
# dawsmith/__init__.py
from dawsmith._native import (
    create_engine as _create_engine,
    get_available_backends,
    Backend,
    Capabilities,
    RenderOptions,
    EditData,
    TrackData,
    MidiNoteData,
)

from dawsmith.validate import validate
from dawsmith.export import dawproject, reaper, ableton, midi, metadata
from dawsmith.batch import BatchRunner

def Engine(backend="auto"):
    """Create a DAWsmith engine.

    Args:
        backend: "auto", "tracktion", or "core"
    """
    backend_enum = {
        "auto": Backend.Auto,
        "tracktion": Backend.Tracktion,
        "core": Backend.Core,
    }[backend.lower()]
    return _create_engine(backend_enum)
```

```python
# dawsmith/edit.py — convenience methods on top of the C++ Edit
class Edit:
    """Pythonic wrapper around the native Edit object."""

    def __init__(self, native_edit):
        self._native = native_edit

    def render_wav(self, path, **kwargs):
        """Convenience: render to WAV with sensible defaults."""
        opts = RenderOptions()
        opts.output_path = path
        for k, v in kwargs.items():
            setattr(opts, k, v)
        self._native.render(opts)

    def export_all(self, output_dir, formats=None):
        """Export to all (or specified) DAW formats + metadata."""
        data = self._native.to_data()
        formats = formats or ["dawproject", "reaper", "midi", "metadata"]

        results = {}
        if "dawproject" in formats:
            path = f"{output_dir}/project.dawproject"
            dawproject.export(data, path)
            results["dawproject"] = path
        if "reaper" in formats:
            path = f"{output_dir}/project.rpp"
            reaper.export(data, path)
            results["reaper"] = path
        if "midi" in formats:
            path = f"{output_dir}/project.mid"
            midi.export(data, path)
            results["midi"] = path
        if "metadata" in formats:
            path = f"{output_dir}/metadata.json"
            metadata.export(data, path)
            results["metadata"] = path

        return results
```

### 4.2 Export Layer

Exporters consume `EditData` structs — plain data with no backend references. This is where the C++ interface design pays off. The `to_data()` method on every C++ object returns a plain struct that crosses the nanobind boundary as a Python object with simple attributes.

```python
# dawsmith/export/dawproject.py
import zipfile
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from dawsmith._native import EditData

def export(edit_data: EditData, output_path: str):
    """Export EditData to a .dawproject file."""
    root = Element("Project", version="1.0")
    root.set("xmlns", "http://www.dawproject.org/dawproject/1.0")

    # Application tag
    app = SubElement(root, "Application")
    app.set("name", "DAWsmith")
    app.set("version", "0.1.0")

    # Transport
    transport = SubElement(root, "Transport")
    if edit_data.tempo_map:
        tempo = SubElement(transport, "Tempo")
        tempo.set("value", str(edit_data.tempo_map[0].bpm))
        tempo.set("unit", "bpm")
    if edit_data.time_signatures:
        ts = edit_data.time_signatures[0]
        time_sig = SubElement(transport, "TimeSignature")
        time_sig.set("numerator", str(ts.numerator))
        time_sig.set("denominator", str(ts.denominator))

    # Structure (tracks)
    structure = SubElement(root, "Structure")
    for track_data in edit_data.tracks:
        _write_track(structure, track_data)

    # Write to zip container
    xml_bytes = tostring(root, encoding="unicode", xml_declaration=True)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.xml", xml_bytes)
        # Include referenced audio files
        for track in edit_data.tracks:
            for clip in track.clips:
                if clip.type == "audio" and clip.audio_file_path:
                    zf.write(clip.audio_file_path,
                            f"audio/{os.path.basename(clip.audio_file_path)}")
```

---

## 5. Backend Repositories

### 5.1 Tracktion Backend

```
dawsmith-tracktion/                    # GPLv3
├── src/
│   ├── tracktion_engine_backend.h     # TracktionEngine : public dawsmith::Engine
│   ├── tracktion_engine_backend.cpp
│   ├── tracktion_edit_backend.h       # TracktionEdit : public dawsmith::Edit
│   ├── tracktion_edit_backend.cpp
│   ├── tracktion_track_backend.h/cpp
│   ├── tracktion_clip_backend.h/cpp
│   ├── tracktion_plugin_backend.h/cpp
│   ├── tracktion_automation_backend.h/cpp
│   ├── export_symbol.cpp             # extern "C" dawsmith_create_engine()
│   └── tracktion_engine/             # Git submodule
├── tests/                            # C++ tests linking against dawsmith.h
│   ├── test_lifecycle.cpp
│   ├── test_render.cpp
│   └── test_midi.cpp
├── CMakeLists.txt                    # Produces libdawsmith_tracktion.so
├── pyproject.toml                    # Wheel that installs the .so alongside dawsmith
└── LICENSE                           # GPLv3
```

The CMakeLists.txt:
- Links against `dawsmith.h` (MIT, header-only)
- Links against Tracktion Engine (GPL submodule)
- Links against JUCE (GPL, via Tracktion Engine)
- Produces a shared library: `libdawsmith_tracktion.so`
- Installs the `.so` to a location on the Python package's library path

### 5.2 Core Backend

```
dawsmith-core/                         # Proprietary
├── src/
│   ├── core_engine.h/cpp             # CoreEngine : public dawsmith::Engine
│   ├── core_edit.h/cpp               # CoreEdit : public dawsmith::Edit
│   ├── core_track.h/cpp
│   ├── core_clip.h/cpp
│   ├── core_plugin.h/cpp
│   ├── core_automation.h/cpp
│   ├── core_renderer.h/cpp           # Offline audio graph rendering
│   ├── core_tempo_map.h/cpp          # Beat ↔ sample conversion
│   ├── core_pdc.h/cpp                # Plugin delay compensation
│   ├── core_graph.h/cpp              # Audio processing graph scheduler
│   ├── export_symbol.cpp             # extern "C" dawsmith_create_engine()
│   └── juce/                         # JUCE (commercial license)
├── tests/
│   ├── test_lifecycle.cpp
│   ├── test_render.cpp
│   └── test_midi.cpp
├── CMakeLists.txt                    # Produces libdawsmith_core.so
├── pyproject.toml
└── LICENSE                           # Proprietary
```

### 5.3 Backend Distribution as Python Wheels

Each backend is distributed as a Python wheel that contains the shared library. When installed via pip, the `.so`/`.dylib`/`.dll` lands in a location that the dawsmith factory's `dlopen` can find.

```toml
# dawsmith-tracktion/pyproject.toml
[project]
name = "dawsmith-tracktion"
version = "0.1.0"
dependencies = ["dawsmith>=0.1.0"]
license = {text = "GPL-3.0-only"}

[tool.setuptools.package-data]
dawsmith_tracktion = ["*.so", "*.dylib", "*.dll"]
```

The dawsmith factory looks for the backend `.so` in:
1. `dawsmith_tracktion` package directory (installed via pip)
2. `dawsmith_core` package directory (installed via pip)
3. `LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` / `PATH` (system paths)
4. Explicit path via `DAWSMITH_BACKEND_PATH` environment variable

---

## 6. Testing Architecture

### 6.1 Three Test Levels

```
Level 1: C++ tests (per backend)
  - Link against dawsmith.h + one backend .so
  - Fast, no Python, run under ASan/TSan/Valgrind
  - Test audio correctness, lifecycle, threading

Level 2: Python tests (shared, parameterized)
  - Import dawsmith, run against whichever backends are installed
  - Test the full stack: Python → nanobind → interface → backend → audio
  - Test exporters, validation, MIR (pure Python)

Level 3: Cross-backend tests (when both installed)
  - Same input to both backends, verify equivalent output
  - Spectral similarity, not bit-identity
```

### 6.2 C++ Test Example

```cpp
// tests/cpp/test_render.cpp
#include <catch2/catch_test_macros.hpp>
#include "dawsmith.h"
#include "dawsmith_factory.h"
#include <sndfile.h>

TEST_CASE("Render produces correct duration", "[render]") {
    auto engine = dawsmith::create_engine();  // loads whichever backend is available
    auto edit = engine->create_edit(44100, 120.0);

    auto* track = edit->insert_audio_track("Test");
    auto* plugin = track->insert_plugin("builtin:tone_generator");
    auto* clip = track->insert_midi_clip("test_clip", 0.0, 4.0);
    clip->add_note(60, 0.0, 4.0, 100);

    dawsmith::RenderOptions opts;
    opts.output_path = "/tmp/dawsmith_test.wav";
    opts.end_beat = 4.0;
    edit->render(opts);

    // Verify duration using libsndfile
    SF_INFO info;
    SNDFILE* f = sf_open("/tmp/dawsmith_test.wav", SFM_READ, &info);
    REQUIRE(f != nullptr);
    double duration = (double)info.frames / info.samplerate;
    REQUIRE(duration == Catch::Approx(2.0).margin(0.01));
    sf_close(f);

    engine->shutdown();
}

TEST_CASE("EditData serialization captures all tracks", "[data]") {
    auto engine = dawsmith::create_engine();
    auto edit = engine->create_edit(44100, 120.0);

    edit->insert_audio_track("Drums");
    edit->insert_audio_track("Bass");
    edit->insert_audio_track("Guitar");

    auto data = edit->to_data();
    REQUIRE(data.tracks.size() == 3);
    REQUIRE(data.tracks[0].name == "Drums");
    REQUIRE(data.tracks[1].name == "Bass");
    REQUIRE(data.tracks[2].name == "Guitar");

    engine->shutdown();
}
```

### 6.3 Python Parameterized Test Example

```python
# tests/conftest.py
import pytest
import dawsmith._native as native

def get_available_backends():
    avail = native.get_available_backends()
    backends = []
    if avail.tracktion:
        backends.append("tracktion")
    if avail.core:
        backends.append("core")
    return backends

@pytest.fixture(params=get_available_backends())
def engine(request, tmp_path):
    """Yields an engine for each available backend."""
    backend = {
        "tracktion": native.Backend.Tracktion,
        "core": native.Backend.Core,
    }[request.param]
    eng = native.create_engine(backend)
    yield eng
    eng.shutdown()
```

```python
# tests/test_render.py
def test_render_correct_duration(engine, tmp_path):
    edit = engine.create_edit(44100, 120.0)
    track = edit.insert_audio_track("Test")
    track.insert_plugin("builtin:tone_generator")
    clip = track.insert_midi_clip("test", 0.0, 4.0)
    clip.add_note(60, 0.0, 4.0, 100)

    out = str(tmp_path / "test.wav")
    opts = dawsmith.RenderOptions()
    opts.output_path = out
    opts.end_beat = 4.0
    edit.render(opts)

    import soundfile as sf
    data, sr = sf.read(out)
    duration = len(data) / sr
    assert abs(duration - 2.0) < 0.01

# This test runs TWICE if both backends are installed — once per backend
```

### 6.4 CI Matrix

```yaml
jobs:
  cpp-tests-tracktion:
    runs-on: [ubuntu-22.04, macos-14, windows-2022]
    steps:
      - cmake --build . --target dawsmith_tracktion_tests
      - ctest

  cpp-tests-core:
    runs-on: [ubuntu-22.04, macos-14, windows-2022]
    steps:
      - cmake --build . --target dawsmith_core_tests
      - ctest

  python-tests-tracktion:
    runs-on: [ubuntu-22.04, macos-14, windows-2022]
    steps:
      - pip install dawsmith dawsmith-tracktion
      - pytest tests/ -k "not cross_backend"

  python-tests-core:
    runs-on: [ubuntu-22.04, macos-14, windows-2022]
    steps:
      - pip install dawsmith dawsmith-core
      - pytest tests/ -k "not cross_backend"

  cross-backend:
    runs-on: ubuntu-22.04
    steps:
      - pip install dawsmith dawsmith-tracktion dawsmith-core
      - pytest tests/test_cross_backend.py

  pure-python:
    runs-on: ubuntu-22.04
    steps:
      - pip install dawsmith
      - pytest tests/test_validation_suite.py tests/test_export_*.py
```

---

## 7. Development Sequence

### Phase 1: Interface + Tracktion Backend (Months 1-4)

| Week | Deliverable |
|---|---|
| 1-2 | `dawsmith.h` interface definition finalized. Data structs defined. Factory header written. |
| 3-4 | nanobind wrapper compiles and exposes all interface types to Python. Backend discovery works (reports "no backend found" gracefully). |
| 5-8 | Tracktion backend implements: Engine, Edit, Track, MidiClip, Plugin (builtin), Render. `dawsmith_create_engine()` export works. |
| 9-10 | C++ test suite for Tracktion backend. 20+ tests passing. |
| 11-12 | Python convenience wrappers. 5 examples. Validation suite (pure Python). |
| 13-16 | `pip install dawsmith dawsmith-tracktion` works on Linux. Python test suite passing. Basic docs. |

**Exit criteria**: `dawsmith.h` is stable. Tracktion backend passes all Phase 1 tests. The interface design is validated by one real implementation.

### Phase 2: Export Layer + Core Backend Scaffolding (Months 4-8)

| Month | dawsmith (MIT) | Tracktion backend (GPL) | Core backend (Proprietary) |
|---|---|---|---|
| 5 | DAWproject exporter | Stable, bug fixes | Project setup, CMake, JUCE commercial license |
| 6 | REAPER RPP exporter, MIDI exporter | Maintenance | CoreEngine lifecycle, CoreEdit scaffolding |
| 7 | Metadata exporter, Ableton ALS (basic) | Maintenance | CoreTrack, CoreMidiClip, CorePlugin (VST3 via JUCE) |
| 8 | Export tests, cross-format consistency | Maintenance | CoreRenderer (sequential, no PDC). **Milestone: basic C++ tests pass.** |

**Exit criteria**: All exporters work with EditData from Tracktion backend. Core backend can render a simple MIDI arrangement through a VST3 instrument. Same C++ tests run against both backends (some still failing on Core — that's expected).

### Phase 3: Core Parity + dawsmith-pro Launch (Months 8-14)

Core backend adds features in priority order. Each feature unlocks more shared tests.

| Feature added to Core | Tests now passing on Core | Month |
|---|---|---|
| Audio clip playback | `test_audio_clip_*` | 9 |
| Automation curves | `test_automation_*` | 9 |
| Tempo map | `test_tempo_*` | 10 |
| Basic PDC | `test_pdc_basic` | 11 |
| Stem export | `test_stem_*` | 11 |
| Time-stretch (Rubber Band) | `test_time_stretch_*` | 12 |
| Multi-threaded graph | `test_performance_*` | 13-14 |

**Parity dashboard tracked in CI:**

```
Feature Parity: dawsmith-core vs dawsmith-tracktion
──────────────────────────────────────────────────
 Feature              Tracktion    Core
 Basic render           ✓           ✓
 MIDI clips             ✓           ✓
 Audio clips            ✓           ✓
 VST3 hosting           ✓           ✓
 Automation             ✓           ✓
 Tempo map              ✓           ✓
 PDC                    ✓           ✓
 Stem export            ✓           ✓
 Time stretch           ✓           ✓
 Multi-thread render    ✓           ✗  ← in progress
 Clip launcher          ✓           ✗  ← not planned
 Recording              ✓           ✗  ← not planned
──────────────────────────────────────────────────
 Commercial parity: 9/9 (100%)
 Full parity: 9/11 (82%)
```

### Phase 4: Core Default + Growth (Months 14-24)

dawsmith-pro switches default backend to Core for new commercial customers. Tracktion backend continues as the open-source offering. Both backends maintained indefinitely — the shared test suite ensures neither regresses.

---

## 8. Package Distribution Summary

### What Users Install

```bash
# Open-source user
pip install dawsmith dawsmith-tracktion
# Installs: dawsmith (MIT) + libdawsmith_tracktion.so (GPL)

# Commercial user
pip install dawsmith dawsmith-core
# Installs: dawsmith (MIT) + libdawsmith_core.so (Proprietary, license key)

# Commercial user with intelligence layer
pip install dawsmith dawsmith-core dawsmith-pro
# Installs: dawsmith (MIT) + libdawsmith_core.so (Proprietary) + dawsmith_pro (Proprietary)

# Convenience extras
pip install dawsmith[open]          # = dawsmith + dawsmith-tracktion
pip install dawsmith[pro]           # = dawsmith + dawsmith-core + dawsmith-pro

# Developer (interface + pure Python only, no audio engine)
pip install dawsmith
# Can use: validation suite, export from EditData, MIR utilities
# Cannot use: Engine, Edit, rendering (raises clear error)
```

### What Gets Built in CI

| Artifact | Contents | Platforms |
|---|---|---|
| `dawsmith` wheel | Python package + `_native.pyd` (nanobind wrapping `dawsmith.h`) | All platforms |
| `dawsmith-tracktion` wheel | `libdawsmith_tracktion.so/.dylib/.dll` | All platforms |
| `dawsmith-core` wheel | `libdawsmith_core.so/.dylib/.dll` | All platforms |
| `dawsmith-pro` wheel | Pure Python | Any (no platform-specific code) |

---

## 9. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Interface language | C++ (`dawsmith.h`) | Single binding layer, C++ tests, multi-language path, compile-time type checking |
| Interface license | MIT | Must be linkable by both GPL and proprietary code without contamination |
| Backend loading | Runtime `dlopen` via factory | No compile-time dependency between backends; swap by installing different wheels |
| Backend export | Single `extern "C"` function | Simplest possible ABI boundary; works across all compilers |
| Data transfer | Plain C++ structs (`EditData` etc.) | Cross the nanobind boundary cleanly; no virtual methods, no backend pointers; exporters consume these directly |
| Python wrapper | Thin convenience layer over nanobind types | Keep binding code minimal; Pythonic sugar in pure Python where it's easy to iterate |
| Test strategy | Shared tests parameterized over backends | Single test suite proves both backends conform to the same contract |
| C++ test framework | Catch2 | Header-only, widely used, good integration with CMake/CTest |
| Python test framework | pytest | Standard, parameterized fixtures, good CI integration |
