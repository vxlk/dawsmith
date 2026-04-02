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
#include <atomic>
#include <mutex>

namespace dawsmith {

namespace te = tracktion;

// ---------------------------------------------------------------------------
// LifetimeGuard -- encapsulates parent-alive checking and own-flag management.
//
//   * Leaf objects (MidiClip, Plugin): construct with parent flag only.
//   * Parent objects (Track, Edit):    construct with parent flag + create_own_flag=true.
//   * Root objects (Engine):           construct with nullptr   + create_own_flag=true.
// ---------------------------------------------------------------------------

class LifetimeGuard {
public:
    explicit LifetimeGuard(std::shared_ptr<std::atomic<bool>> parent_alive,
                           bool create_own_flag = false)
        : parent_alive_(std::move(parent_alive))
    {
        if (create_own_flag)
            alive_ = std::make_shared<std::atomic<bool>>(true);
    }

    ~LifetimeGuard() { invalidate(); }

    LifetimeGuard(const LifetimeGuard&) = delete;
    LifetimeGuard& operator=(const LifetimeGuard&) = delete;
    LifetimeGuard(LifetimeGuard&&) noexcept = default;
    LifetimeGuard& operator=(LifetimeGuard&&) noexcept = default;

    // Check that the parent is still alive.  ExceptionT defaults to
    // ObjectDeletedError; Edit overrides with EngineDestroyedError.
    template <typename ExceptionT = ObjectDeletedError>
    void check(const char* msg) const {
        if (parent_alive_ && !parent_alive_->load(std::memory_order_acquire))
            throw ExceptionT(msg);
    }

    // Mark this object as dead.  Idempotent -- safe to call from destructor
    // body AND again when the member is implicitly destroyed.
    void invalidate() noexcept {
        if (alive_)
            alive_->store(false, std::memory_order_release);
    }

    // The flag that children should hold.
    std::shared_ptr<std::atomic<bool>> flag() const { return alive_; }

private:
    std::shared_ptr<std::atomic<bool>> parent_alive_;
    std::shared_ptr<std::atomic<bool>> alive_;
};

// ---------------------------------------------------------------------------
// Tracktion wrapper classes
// ---------------------------------------------------------------------------

class TracktionMidiClip : public MidiClip {
public:
    TracktionMidiClip(te::MidiClip::Ptr clip, te::Edit& edit,
                      std::shared_ptr<std::atomic<bool>> parent_alive);
    void add_note(int pitch, double start_beat, double length_beats,
                  int velocity) override;
    void clear_notes() override;
    std::string get_name() const override;

private:
    te::MidiClip::Ptr clip_;
    te::Edit& edit_;
    LifetimeGuard lifetime_;
};

class TracktionAudioClip : public AudioClip {
public:
    TracktionAudioClip(te::WaveAudioClip::Ptr clip, te::Edit& edit,
                       std::shared_ptr<std::atomic<bool>> parent_alive);
    std::string get_name() const override;
    std::string get_file_path() const override;
    double get_start_beat() const override;
    double get_length_beats() const override;
    void set_gain(double linear) override;
    double get_gain() const override;
    void set_loop(bool looping) override;
    bool get_loop() const override;

private:
    te::WaveAudioClip::Ptr clip_;
    te::Edit& edit_;
    LifetimeGuard lifetime_;
};

class TracktionPlugin : public Plugin {
public:
    TracktionPlugin(te::Plugin::Ptr plugin,
                    std::shared_ptr<std::atomic<bool>> parent_alive);
    std::string get_name() const override;
    int get_parameter_count() const override;
    std::string get_parameter_name(int index) const override;
    float get_parameter_value(int index) const override;
    void set_parameter_value(int index, float value) override;
    bool is_loaded() const override;

private:
    te::Plugin::Ptr plugin_;
    LifetimeGuard lifetime_;
};

class TracktionTrack : public Track {
public:
    TracktionTrack(te::AudioTrack* track, te::Edit& edit,
                   te::Engine& engine,
                   std::shared_ptr<std::atomic<bool>> parent_alive);
    ~TracktionTrack() override;
    std::string get_name() const override;
    MidiClip* insert_midi_clip(const std::string& name,
                               double start_beat,
                               double length_beats) override;
    AudioClip* insert_audio_clip(const std::string& name,
                                  const std::string& file_path,
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
    LifetimeGuard lifetime_;   // parent flag + own flag for children
    std::vector<std::unique_ptr<TracktionMidiClip>> clips_;
    std::vector<std::unique_ptr<TracktionAudioClip>> audio_clips_;
    std::vector<std::unique_ptr<TracktionPlugin>> plugins_;
};

class TracktionEdit : public Edit {
public:
    TracktionEdit(std::unique_ptr<te::Edit> edit,
                  std::shared_ptr<te::Engine> engine,
                  std::shared_ptr<juce::ScopedJuceInitialiser_GUI> juce_init,
                  std::shared_ptr<std::atomic<bool>> engine_alive);
    ~TracktionEdit() override;
    Track* insert_audio_track(const std::string& name) override;
    void set_tempo(double bpm) override;
    void render(const RenderOptions& options) override;
    void play() override;
    void stop() override;
    bool is_playing() const override;
    double get_position_seconds() const override;

private:
    // Declaration order matters for destruction: juce_init_ destroyed LAST.
    std::shared_ptr<juce::ScopedJuceInitialiser_GUI> juce_init_;  // JUCE lifetime
    std::shared_ptr<te::Engine> engine_;
    std::unique_ptr<te::Edit> edit_;
    LifetimeGuard lifetime_;   // engine-alive flag + own flag for children
    std::vector<std::unique_ptr<TracktionTrack>> tracks_;
};

// Shared JUCE initialiser -- ensures JUCE lives as long as any Engine or Edit.
std::shared_ptr<juce::ScopedJuceInitialiser_GUI> get_shared_juce_init();

class TracktionEngine : public Engine {
public:
    explicit TracktionEngine(const std::string& app_name);
    ~TracktionEngine() override;
    std::unique_ptr<Edit> create_edit(double bpm) override;
    void scan_plugins(const std::string& path) override;
    std::vector<PluginDescription> get_available_plugins() const override;

private:
    // Declaration order: juce_init_ destroyed LAST, engine_ before it.
    std::shared_ptr<juce::ScopedJuceInitialiser_GUI> juce_init_;
    std::shared_ptr<te::Engine> engine_;
    LifetimeGuard lifetime_{nullptr, true};  // root: no parent, creates own flag
};

}  // namespace dawsmith
