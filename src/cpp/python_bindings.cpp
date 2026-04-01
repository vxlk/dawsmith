// python_bindings.cpp -- nanobind wrappers for dawsmith interface
// License: GPL-3.0-or-later

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/unique_ptr.h>

#include "dawsmith.h"

namespace nb = nanobind;
using namespace dawsmith;

NB_MODULE(_native, m) {
    m.doc() = "DAWsmith native bindings";

    // Register custom exceptions so Python gets clean types.
    nb::exception<EngineDestroyedError>(m, "EngineDestroyedError",
                                         PyExc_RuntimeError);
    nb::exception<ObjectDeletedError>(m, "ObjectDeletedError",
                                       PyExc_RuntimeError);

    nb::class_<PluginDescription>(m, "PluginDescription")
        .def_ro("name", &PluginDescription::name)
        .def_ro("manufacturer", &PluginDescription::manufacturer)
        .def_ro("identifier", &PluginDescription::identifier)
        .def_ro("format", &PluginDescription::format)
        .def_ro("is_instrument", &PluginDescription::is_instrument)
        .def("__repr__", [](const PluginDescription& d) {
            return "<PluginDescription '" + d.name + "' (" + d.format + ")>";
        });

    nb::class_<RenderOptions>(m, "RenderOptions")
        .def(nb::init<>())
        .def_rw("output_path", &RenderOptions::output_path)
        .def_rw("sample_rate", &RenderOptions::sample_rate)
        .def_rw("bit_depth", &RenderOptions::bit_depth)
        .def_rw("start_seconds", &RenderOptions::start_seconds)
        .def_rw("end_seconds", &RenderOptions::end_seconds);

    nb::class_<MidiClip>(m, "MidiClip")
        .def("add_note", &MidiClip::add_note,
             nb::arg("pitch"), nb::arg("start_beat"),
             nb::arg("length_beats"), nb::arg("velocity") = 100)
        .def("clear_notes", &MidiClip::clear_notes)
        .def("get_name", &MidiClip::get_name);

    nb::class_<Plugin>(m, "Plugin")
        .def("get_name", &Plugin::get_name)
        .def("get_parameter_count", &Plugin::get_parameter_count)
        .def("get_parameter_name", &Plugin::get_parameter_name)
        .def("get_parameter_value", &Plugin::get_parameter_value)
        .def("set_parameter_value", &Plugin::set_parameter_value)
        .def("is_loaded", &Plugin::is_loaded);

    nb::class_<Track>(m, "Track")
        .def("get_name", &Track::get_name)
        .def("insert_midi_clip", &Track::insert_midi_clip,
             nb::rv_policy::reference_internal,   // ref + keep Track alive
             nb::arg("name"), nb::arg("start_beat"),
             nb::arg("length_beats"))
        .def("insert_plugin", &Track::insert_plugin,
             nb::rv_policy::reference_internal,   // ref + keep Track alive
             nb::arg("identifier"))
        .def("set_volume", &Track::set_volume)
        .def("set_pan", &Track::set_pan)
        .def("set_mute", &Track::set_mute);

    nb::class_<Edit>(m, "Edit")
        .def("insert_audio_track", &Edit::insert_audio_track,
             nb::rv_policy::reference_internal,   // ref + keep Edit alive
             nb::arg("name"))
        .def("set_tempo", &Edit::set_tempo)
        .def("render", &Edit::render)
        .def("play", &Edit::play)
        .def("stop", &Edit::stop)
        .def("is_playing", &Edit::is_playing)
        .def("get_position_seconds", &Edit::get_position_seconds);

    nb::class_<Engine>(m, "Engine")
        .def("create_edit", &Engine::create_edit,
             nb::keep_alive<0, 1>(),              // Edit keeps Engine alive
             nb::arg("bpm") = 120.0)
        .def("scan_plugins", &Engine::scan_plugins,
             nb::arg("path") = "")
        .def("get_available_plugins", &Engine::get_available_plugins);

    m.def("create_engine", &create_engine,
          nb::arg("app_name") = "DAWsmith",
          "Create a DAWsmith engine instance.");
}
