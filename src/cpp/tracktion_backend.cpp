// tracktion_backend.cpp -- Tracktion Engine implementation of dawsmith interface
// License: GPL-3.0-or-later

#include "tracktion_backend.h"

#include <juce_audio_formats/juce_audio_formats.h>
#include <stdexcept>

namespace dawsmith {

namespace te = tracktion;

// ---------------------------------------------------------------------------
// Shared JUCE initialiser (singleton via weak_ptr)
// ---------------------------------------------------------------------------

std::shared_ptr<juce::ScopedJuceInitialiser_GUI> get_shared_juce_init() {
    static std::mutex mtx;
    static std::weak_ptr<juce::ScopedJuceInitialiser_GUI> s_instance;
    std::lock_guard<std::mutex> lock(mtx);
    auto ptr = s_instance.lock();
    if (!ptr) {
        ptr = std::make_shared<juce::ScopedJuceInitialiser_GUI>();
        s_instance = ptr;
    }
    return ptr;
}

// ---------------------------------------------------------------------------
// TracktionMidiClip
// ---------------------------------------------------------------------------

TracktionMidiClip::TracktionMidiClip(te::MidiClip::Ptr clip, te::Edit& edit,
                                      std::shared_ptr<std::atomic<bool>> parent_alive)
    : clip_(clip), edit_(edit), lifetime_(std::move(parent_alive)) {}

void TracktionMidiClip::add_note(int pitch, double start_beat,
                                  double length_beats, int velocity) {
    lifetime_.check("Parent Track has been deleted");
    if (!clip_) return;
    auto& sequence = clip_->getSequence();
    sequence.addNote(
        pitch,
        te::BeatPosition::fromBeats(start_beat),
        te::BeatDuration::fromBeats(length_beats),
        velocity,
        0,        // colour index
        nullptr); // no UndoManager
}

void TracktionMidiClip::clear_notes() {
    lifetime_.check("Parent Track has been deleted");
    if (!clip_) return;
    clip_->getSequence().clear(nullptr);
}

std::string TracktionMidiClip::get_name() const {
    lifetime_.check("Parent Track has been deleted");
    if (!clip_) return "";
    return clip_->getName().toStdString();
}

// ---------------------------------------------------------------------------
// TracktionPlugin
// ---------------------------------------------------------------------------

TracktionPlugin::TracktionPlugin(te::Plugin::Ptr plugin,
                                  std::shared_ptr<std::atomic<bool>> parent_alive)
    : plugin_(plugin), lifetime_(std::move(parent_alive)) {}

std::string TracktionPlugin::get_name() const {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return "";
    return plugin_->getName().toStdString();
}

int TracktionPlugin::get_parameter_count() const {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return 0;
    return plugin_->getAutomatableParameters().size();
}

std::string TracktionPlugin::get_parameter_name(int index) const {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return "";
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return "";
    return params[index]->getParameterName().toStdString();
}

float TracktionPlugin::get_parameter_value(int index) const {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return 0.0f;
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return 0.0f;
    return params[index]->getCurrentValue();
}

void TracktionPlugin::set_parameter_value(int index, float value) {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return;
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return;
    params[index]->setParameter(value, juce::sendNotification);
}

bool TracktionPlugin::is_loaded() const {
    lifetime_.check("Parent Track has been deleted");
    if (!plugin_) return false;
    return true;
}

// ---------------------------------------------------------------------------
// TracktionTrack
// ---------------------------------------------------------------------------

TracktionTrack::TracktionTrack(te::AudioTrack* track, te::Edit& edit,
                               te::Engine& engine,
                               std::shared_ptr<std::atomic<bool>> parent_alive)
    : track_(track), edit_(edit), engine_(engine),
      lifetime_(std::move(parent_alive), true) {}

TracktionTrack::~TracktionTrack() {
    lifetime_.invalidate();
}

std::string TracktionTrack::get_name() const {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return "";
    return track_->getName().toStdString();
}

MidiClip* TracktionTrack::insert_midi_clip(const std::string& name,
                                            double start_beat,
                                            double length_beats) {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return nullptr;

    auto& tempoSeq = edit_.tempoSequence;
    auto startTime = tempoSeq.beatsToTime(te::BeatPosition::fromBeats(start_beat));
    auto endTime = tempoSeq.beatsToTime(
        te::BeatPosition::fromBeats(start_beat + length_beats));

    te::TimeRange clipRange(startTime, endTime);
    auto clipRef = track_->insertMIDIClip(clipRange, nullptr);

    if (clipRef != nullptr)
        clipRef->setName(juce::String(name));

    auto wrapper = std::make_unique<TracktionMidiClip>(clipRef, edit_,
                                                        lifetime_.flag());
    auto* ptr = wrapper.get();
    clips_.push_back(std::move(wrapper));
    return ptr;
}

Plugin* TracktionTrack::insert_plugin(const std::string& identifier) {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return nullptr;

    te::Plugin::Ptr plugin;

    // Try to find in known plugin list (VST3, etc.)
    auto& pm = engine_.getPluginManager();
    auto& kpl = pm.knownPluginList;
    auto types = kpl.getTypes();

    for (auto& desc : types) {
        if (desc.fileOrIdentifier.toStdString() == identifier ||
            desc.name.toStdString() == identifier) {
            // Create external plugin from description
            plugin = edit_.getPluginCache().createNewPlugin(
                te::ExternalPlugin::xmlTypeName, desc);
            break;
        }
    }

    if (!plugin) {
        throw std::runtime_error(
            "Plugin not found: " + identifier +
            ". Run engine.scan_plugins() first.");
    }

    track_->pluginList.insertPlugin(plugin, -1, nullptr);

    auto wrapper = std::make_unique<TracktionPlugin>(plugin, lifetime_.flag());
    auto* ptr = wrapper.get();
    plugins_.push_back(std::move(wrapper));
    return ptr;
}

void TracktionTrack::set_volume(double linear) {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return;
    if (auto vol = track_->getVolumePlugin()) {
        float db = (linear <= 0.0) ? -100.0f
                   : static_cast<float>(juce::Decibels::gainToDecibels(linear));
        vol->setVolumeDb(db);
    }
}

void TracktionTrack::set_pan(double pan) {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return;
    if (auto vol = track_->getVolumePlugin()) {
        vol->setPan(static_cast<float>(pan));
    }
}

void TracktionTrack::set_mute(bool muted) {
    lifetime_.check("Parent Edit has been deleted");
    if (!track_) return;
    track_->setMute(muted);
}

// ---------------------------------------------------------------------------
// TracktionEdit
// ---------------------------------------------------------------------------

TracktionEdit::TracktionEdit(std::unique_ptr<te::Edit> edit,
                             std::shared_ptr<te::Engine> engine,
                             std::shared_ptr<juce::ScopedJuceInitialiser_GUI> juce_init,
                             std::shared_ptr<std::atomic<bool>> engine_alive)
    : juce_init_(std::move(juce_init)),
      engine_(std::move(engine)),
      edit_(std::move(edit)),
      lifetime_(std::move(engine_alive), true) {}

TracktionEdit::~TracktionEdit() {
    lifetime_.invalidate();
    // Ensure children are destroyed before the edit/engine they reference.
    tracks_.clear();
    edit_.reset();
    // engine_ and juce_init_ released implicitly in reverse declaration order.
}

Track* TracktionEdit::insert_audio_track(const std::string& name) {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return nullptr;

    edit_->ensureNumberOfAudioTracks(
        static_cast<int>(edit_->getTrackList().size()) + 1);

    // Get the last audio track (the one just created)
    auto tracks = te::getAudioTracks(*edit_);
    if (tracks.isEmpty()) return nullptr;

    auto* audioTrack = tracks.getLast();
    audioTrack->setName(juce::String(name));

    auto wrapper = std::make_unique<TracktionTrack>(audioTrack, *edit_, *engine_,
                                                     lifetime_.flag());
    auto* ptr = wrapper.get();
    tracks_.push_back(std::move(wrapper));
    return ptr;
}

void TracktionEdit::set_tempo(double bpm) {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return;
    edit_->tempoSequence.getTempo(0)->setBpm(bpm);
}

void TracktionEdit::render(const RenderOptions& options) {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return;

    juce::File outputFile;
    if (juce::File::isAbsolutePath(juce::String(options.output_path)))
        outputFile = juce::File(options.output_path);
    else
        outputFile = juce::File::getCurrentWorkingDirectory()
                         .getChildFile(juce::String(options.output_path));

    // Delete existing file if present
    outputFile.deleteFile();

    // Use the simple Edit-level render (renders entire edit to WAV)
    bool success = te::Renderer::renderToFile(*edit_, outputFile, false);

    if (!success || !outputFile.existsAsFile()) {
        throw std::runtime_error(
            "Render failed — output file not created: " +
            outputFile.getFullPathName().toStdString());
    }
}

// Message-pump rationale:
// JUCE has no promise/future system for message dispatch.  Its internal state
// changes (audio-device init, transport start/stop, ValueTree listeners) are
// all delivered through a single-threaded message loop -- designed for GUI apps
// where the loop runs forever.  DAWsmith is headless, so no loop is running.
// We manually pump in small slices until the desired state is reached.
//
// Future improvement: expose an explicit engine.pump() to Python and/or run
// the MessageManager on a dedicated background thread so Python calls can
// post work and await a semaphore instead of blocking here.

void TracktionEdit::play() {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return;

    auto* mm = juce::MessageManager::getInstanceWithoutCreating();

    // Dispatch any pending device-initialisation callbacks.
    if (mm) mm->runDispatchLoopUntil(50);

    auto& transport = edit_->getTransport();
    transport.setPosition(te::TimePosition::fromSeconds(0.0));
    transport.play(false);

    // Pump until transport confirms playing, with timeout.
    if (mm) {
        constexpr int timeout_ms = 2000;
        auto start = juce::Time::getMillisecondCounter();
        while (!transport.isPlaying()) {
            mm->runDispatchLoopUntil(10);
            if (static_cast<int>(juce::Time::getMillisecondCounter() - start) > timeout_ms)
                break;
        }
    }
}

void TracktionEdit::stop() {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return;

    auto& transport = edit_->getTransport();
    transport.stop(false, false);

    // Pump until transport confirms stopped, with timeout.
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating()) {
        constexpr int timeout_ms = 500;
        auto start = juce::Time::getMillisecondCounter();
        while (transport.isPlaying()) {
            mm->runDispatchLoopUntil(10);
            if (static_cast<int>(juce::Time::getMillisecondCounter() - start) > timeout_ms)
                break;
        }
    }
}

bool TracktionEdit::is_playing() const {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return false;
    // Pump message loop so transport state stays current
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(1);
    return edit_->getTransport().isPlaying();
}

double TracktionEdit::get_position_seconds() const {
    lifetime_.check<EngineDestroyedError>("Engine has been destroyed");
    if (!edit_) return 0.0;
    // Pump message loop so position updates flow from audio thread
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(1);
    return edit_->getTransport().getPosition().inSeconds();
}

// ---------------------------------------------------------------------------
// TracktionEngine
// ---------------------------------------------------------------------------

TracktionEngine::TracktionEngine(const std::string& app_name)
    : juce_init_(get_shared_juce_init()),
      engine_(std::make_shared<te::Engine>(
          juce::String(app_name),
          nullptr,   // no PropertyStorage
          nullptr))  // no UIBehaviour
{
}

TracktionEngine::~TracktionEngine() {
    lifetime_.invalidate();
    engine_.reset();
    // juce_init_ released implicitly -- JUCE stays alive if Edits still hold it.
}

std::unique_ptr<Edit> TracktionEngine::create_edit(double bpm) {
    auto tempFile = juce::File::getSpecialLocation(
        juce::File::tempDirectory)
        .getChildFile("dawsmith_edit_" + juce::String(juce::Random::getSystemRandom().nextInt()) + ".tracktionedit");

    auto edit = te::createEmptyEdit(*engine_, tempFile);
    edit->tempoSequence.getTempo(0)->setBpm(bpm);

    return std::make_unique<TracktionEdit>(std::move(edit), engine_,
                                            juce_init_, lifetime_.flag());
}

void TracktionEngine::scan_plugins(const std::string& path) {
    auto& pm = engine_->getPluginManager();

    // Ensure VST3 format is registered
    pm.pluginFormatManager.addDefaultFormats();

    juce::String scanPath;
    if (path.empty()) {
#if JUCE_WINDOWS
        scanPath = "C:\\Program Files\\Common Files\\VST3";
#elif JUCE_MAC
        scanPath = "~/Library/Audio/Plug-Ins/VST3";
#else
        scanPath = "/usr/lib/vst3";
#endif
    } else {
        scanPath = juce::String(path);
    }

    juce::FileSearchPath searchPath(scanPath);

    for (int i = 0; i < pm.pluginFormatManager.getNumFormats(); ++i) {
        auto* format = pm.pluginFormatManager.getFormat(i);
        juce::PluginDirectoryScanner scanner(
            pm.knownPluginList,
            *format,
            searchPath,
            true,                    // recursive
            juce::File());           // dead plugin list file

        juce::String pluginName;
        while (scanner.scanNextFile(true, pluginName)) {
            // scanning...
        }
    }
}

std::vector<PluginDescription> TracktionEngine::get_available_plugins() const {
    auto& pm = engine_->getPluginManager();
    auto types = pm.knownPluginList.getTypes();

    std::vector<PluginDescription> result;
    result.reserve(types.size());

    for (auto& desc : types) {
        PluginDescription d;
        d.name = desc.name.toStdString();
        d.manufacturer = desc.manufacturerName.toStdString();
        d.identifier = desc.fileOrIdentifier.toStdString();
        d.format = desc.pluginFormatName.toStdString();
        d.is_instrument = desc.isInstrument;
        result.push_back(std::move(d));
    }

    return result;
}

// ---------------------------------------------------------------------------
// Factory function
// ---------------------------------------------------------------------------

std::unique_ptr<Engine> create_engine(const std::string& app_name) {
    return std::make_unique<TracktionEngine>(app_name);
}

}  // namespace dawsmith
