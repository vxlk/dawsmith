// tracktion_backend.cpp -- Tracktion Engine implementation of dawsmith interface
// License: GPL-3.0-or-later

#include "tracktion_backend.h"

#include <juce_audio_formats/juce_audio_formats.h>
#include <stdexcept>

namespace dawsmith {

namespace te = tracktion;

// ---------------------------------------------------------------------------
// TracktionMidiClip
// ---------------------------------------------------------------------------

TracktionMidiClip::TracktionMidiClip(te::MidiClip::Ptr clip, te::Edit& edit)
    : clip_(clip), edit_(edit) {}

void TracktionMidiClip::add_note(int pitch, double start_beat,
                                  double length_beats, int velocity) {
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
    if (!clip_) return;
    clip_->getSequence().clear(nullptr);
}

std::string TracktionMidiClip::get_name() const {
    if (!clip_) return "";
    return clip_->getName().toStdString();
}

// ---------------------------------------------------------------------------
// TracktionPlugin
// ---------------------------------------------------------------------------

TracktionPlugin::TracktionPlugin(te::Plugin::Ptr plugin)
    : plugin_(plugin) {}

std::string TracktionPlugin::get_name() const {
    if (!plugin_) return "";
    return plugin_->getName().toStdString();
}

int TracktionPlugin::get_parameter_count() const {
    if (!plugin_) return 0;
    return plugin_->getAutomatableParameters().size();
}

std::string TracktionPlugin::get_parameter_name(int index) const {
    if (!plugin_) return "";
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return "";
    return params[index]->getParameterName().toStdString();
}

float TracktionPlugin::get_parameter_value(int index) const {
    if (!plugin_) return 0.0f;
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return 0.0f;
    return params[index]->getCurrentValue();
}

void TracktionPlugin::set_parameter_value(int index, float value) {
    if (!plugin_) return;
    auto params = plugin_->getAutomatableParameters();
    if (index < 0 || index >= params.size()) return;
    params[index]->setParameter(value, juce::sendNotification);
}

bool TracktionPlugin::is_loaded() const {
    if (!plugin_) return false;
    return true;
}

// ---------------------------------------------------------------------------
// TracktionTrack
// ---------------------------------------------------------------------------

TracktionTrack::TracktionTrack(te::AudioTrack* track, te::Edit& edit,
                               te::Engine& engine)
    : track_(track), edit_(edit), engine_(engine) {}

std::string TracktionTrack::get_name() const {
    if (!track_) return "";
    return track_->getName().toStdString();
}

MidiClip* TracktionTrack::insert_midi_clip(const std::string& name,
                                            double start_beat,
                                            double length_beats) {
    if (!track_) return nullptr;

    auto& tempoSeq = edit_.tempoSequence;
    auto startTime = tempoSeq.beatsToTime(te::BeatPosition::fromBeats(start_beat));
    auto endTime = tempoSeq.beatsToTime(
        te::BeatPosition::fromBeats(start_beat + length_beats));

    te::TimeRange clipRange(startTime, endTime);
    auto clipRef = track_->insertMIDIClip(clipRange, nullptr);

    if (clipRef != nullptr)
        clipRef->setName(juce::String(name));

    auto wrapper = std::make_unique<TracktionMidiClip>(clipRef, edit_);
    auto* ptr = wrapper.get();
    clips_.push_back(std::move(wrapper));
    return ptr;
}

Plugin* TracktionTrack::insert_plugin(const std::string& identifier) {
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

    auto wrapper = std::make_unique<TracktionPlugin>(plugin);
    auto* ptr = wrapper.get();
    plugins_.push_back(std::move(wrapper));
    return ptr;
}

void TracktionTrack::set_volume(double linear) {
    if (!track_) return;
    if (auto vol = track_->getVolumePlugin()) {
        float db = (linear <= 0.0) ? -100.0f
                   : static_cast<float>(juce::Decibels::gainToDecibels(linear));
        vol->setVolumeDb(db);
    }
}

void TracktionTrack::set_pan(double pan) {
    if (!track_) return;
    if (auto vol = track_->getVolumePlugin()) {
        vol->setPan(static_cast<float>(pan));
    }
}

void TracktionTrack::set_mute(bool muted) {
    if (!track_) return;
    track_->setMute(muted);
}

// ---------------------------------------------------------------------------
// TracktionEdit
// ---------------------------------------------------------------------------

TracktionEdit::TracktionEdit(std::unique_ptr<te::Edit> edit,
                             std::shared_ptr<te::Engine> engine)
    : edit_(std::move(edit)), engine_(std::move(engine)) {}

TracktionEdit::~TracktionEdit() {
    // Ensure edit is destroyed before engine (edit references engine internals)
    tracks_.clear();
    edit_.reset();
}

Track* TracktionEdit::insert_audio_track(const std::string& name) {
    if (!edit_) return nullptr;

    edit_->ensureNumberOfAudioTracks(
        static_cast<int>(edit_->getTrackList().size()) + 1);

    // Get the last audio track (the one just created)
    auto tracks = te::getAudioTracks(*edit_);
    if (tracks.isEmpty()) return nullptr;

    auto* audioTrack = tracks.getLast();
    audioTrack->setName(juce::String(name));

    auto wrapper = std::make_unique<TracktionTrack>(audioTrack, *edit_, *engine_);
    auto* ptr = wrapper.get();
    tracks_.push_back(std::move(wrapper));
    return ptr;
}

void TracktionEdit::set_tempo(double bpm) {
    if (!edit_) return;
    edit_->tempoSequence.getTempo(0)->setBpm(bpm);
}

void TracktionEdit::render(const RenderOptions& options) {
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

void TracktionEdit::play() {
    if (!edit_) return;

    // In a headless Python host, the JUCE message loop isn't running.
    // Pump it before play to ensure the audio device is fully initialized
    // (DeviceManager setup involves async callbacks that need dispatching).
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(200);

    auto& transport = edit_->getTransport();
    transport.setPosition(te::TimePosition::fromSeconds(0.0));
    transport.play(false);

    // Pump again so transport state changes and EditPlaybackContext setup
    // (triggered by ValueTree listeners) can complete.
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(200);
}

void TracktionEdit::stop() {
    if (!edit_) return;
    edit_->getTransport().stop(false, false);

    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(50);
}

bool TracktionEdit::is_playing() const {
    if (!edit_) return false;
    // Pump message loop so transport state stays current
    if (auto* mm = juce::MessageManager::getInstanceWithoutCreating())
        mm->runDispatchLoopUntil(1);
    return edit_->getTransport().isPlaying();
}

double TracktionEdit::get_position_seconds() const {
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
    : engine_(std::make_shared<te::Engine>(
          juce::String(app_name),
          nullptr,   // no PropertyStorage
          nullptr))  // no UIBehaviour
{
}

TracktionEngine::~TracktionEngine() {
    engine_.reset();
}

std::unique_ptr<Edit> TracktionEngine::create_edit(double bpm) {
    auto tempFile = juce::File::getSpecialLocation(
        juce::File::tempDirectory)
        .getChildFile("dawsmith_edit_" + juce::String(juce::Random::getSystemRandom().nextInt()) + ".tracktionedit");

    auto edit = te::createEmptyEdit(*engine_, tempFile);
    edit->tempoSequence.getTempo(0)->setBpm(bpm);

    return std::make_unique<TracktionEdit>(std::move(edit), engine_);
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
