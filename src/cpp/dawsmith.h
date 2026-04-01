// dawsmith.h -- Abstract C++ interface for programmatic music production
// License: MIT
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <stdexcept>

namespace dawsmith {

// Exception thrown when accessing an object whose Engine has been destroyed.
class EngineDestroyedError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

// Exception thrown when accessing a child object whose parent has been deleted.
class ObjectDeletedError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct PluginDescription {
    std::string name;
    std::string manufacturer;
    std::string identifier;
    std::string format;       // "VST3", "AU", "builtin"
    bool is_instrument = false;
};

struct RenderOptions {
    std::string output_path;
    int sample_rate = 44100;
    int bit_depth = 16;
    double start_seconds = 0.0;
    double end_seconds = -1.0;  // -1 = render to end of last clip
};

class MidiClip {
public:
    virtual ~MidiClip() = default;
    virtual void add_note(int pitch, double start_beat, double length_beats,
                          int velocity = 100) = 0;
    virtual void clear_notes() = 0;
    virtual std::string get_name() const = 0;
};

class Plugin {
public:
    virtual ~Plugin() = default;
    virtual std::string get_name() const = 0;
    virtual int get_parameter_count() const = 0;
    virtual std::string get_parameter_name(int index) const = 0;
    virtual float get_parameter_value(int index) const = 0;
    virtual void set_parameter_value(int index, float value) = 0;
    virtual bool is_loaded() const = 0;
};

class Track {
public:
    virtual ~Track() = default;
    virtual std::string get_name() const = 0;
    virtual MidiClip* insert_midi_clip(const std::string& name,
                                       double start_beat,
                                       double length_beats) = 0;
    virtual Plugin* insert_plugin(const std::string& identifier) = 0;
    virtual void set_volume(double linear) = 0;
    virtual void set_pan(double pan) = 0;
    virtual void set_mute(bool muted) = 0;
};

class Edit {
public:
    virtual ~Edit() = default;
    virtual Track* insert_audio_track(const std::string& name) = 0;
    virtual void set_tempo(double bpm) = 0;
    virtual void render(const RenderOptions& options) = 0;
    virtual void play() = 0;
    virtual void stop() = 0;
    virtual bool is_playing() const = 0;
    virtual double get_position_seconds() const = 0;
};

class Engine {
public:
    virtual ~Engine() = default;
    virtual std::unique_ptr<Edit> create_edit(double bpm = 120.0) = 0;
    virtual void scan_plugins(const std::string& path = "") = 0;
    virtual std::vector<PluginDescription> get_available_plugins() const = 0;
};

// Factory function -- creates the Tracktion Engine backend
std::unique_ptr<Engine> create_engine(const std::string& app_name = "DAWsmith");

}  // namespace dawsmith
