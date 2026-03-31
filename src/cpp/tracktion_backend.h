// tracktion_backend.h -- Tracktion Engine implementation of dawsmith interface
// License: GPL-3.0-or-later
#pragma once

#include "dawsmith.h"

#include <juce_core/juce_core.h>
#include <juce_audio_devices/juce_audio_devices.h>
#include <juce_audio_processors/juce_audio_processors.h>
#include <tracktion_engine/tracktion_engine.h>

#include <vector>
#include <memory>

namespace dawsmith {

namespace te = tracktion;

class TracktionMidiClip : public MidiClip {
public:
    explicit TracktionMidiClip(te::MidiClip::Ptr clip, te::Edit& edit);
    void add_note(int pitch, double start_beat, double length_beats,
                  int velocity) override;
    void clear_notes() override;
    std::string get_name() const override;

private:
    te::MidiClip::Ptr clip_;
    te::Edit& edit_;
};

class TracktionPlugin : public Plugin {
public:
    explicit TracktionPlugin(te::Plugin::Ptr plugin);
    std::string get_name() const override;
    int get_parameter_count() const override;
    std::string get_parameter_name(int index) const override;
    float get_parameter_value(int index) const override;
    void set_parameter_value(int index, float value) override;
    bool is_loaded() const override;

private:
    te::Plugin::Ptr plugin_;
};

class TracktionTrack : public Track {
public:
    TracktionTrack(te::AudioTrack* track, te::Edit& edit,
                   te::Engine& engine);
    std::string get_name() const override;
    MidiClip* insert_midi_clip(const std::string& name,
                               double start_beat,
                               double length_beats) override;
    Plugin* insert_plugin(const std::string& identifier) override;
    void set_volume(double linear) override;
    void set_pan(double pan) override;
    void set_mute(bool muted) override;

private:
    te::AudioTrack* track_;
    te::Edit& edit_;
    te::Engine& engine_;
    std::vector<std::unique_ptr<TracktionMidiClip>> clips_;
    std::vector<std::unique_ptr<TracktionPlugin>> plugins_;
};

class TracktionEdit : public Edit {
public:
    TracktionEdit(std::unique_ptr<te::Edit> edit,
                  std::shared_ptr<te::Engine> engine);
    ~TracktionEdit() override;
    Track* insert_audio_track(const std::string& name) override;
    void set_tempo(double bpm) override;
    void render(const RenderOptions& options) override;
    void play() override;
    void stop() override;
    bool is_playing() const override;
    double get_position_seconds() const override;

private:
    std::unique_ptr<te::Edit> edit_;
    std::shared_ptr<te::Engine> engine_;  // shared to outlive edits
    std::vector<std::unique_ptr<TracktionTrack>> tracks_;
};

class TracktionEngine : public Engine {
public:
    explicit TracktionEngine(const std::string& app_name);
    ~TracktionEngine() override;
    std::unique_ptr<Edit> create_edit(double bpm) override;
    void scan_plugins(const std::string& path) override;
    std::vector<PluginDescription> get_available_plugins() const override;

private:
    juce::ScopedJuceInitialiser_GUI juce_init_;
    std::shared_ptr<te::Engine> engine_;  // shared with edits
};

}  // namespace dawsmith
