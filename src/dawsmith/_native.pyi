"""Type stubs for the DAWsmith native C++ extension module."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal


class EngineDestroyedError(RuntimeError):
    """Raised when accessing the engine after it has been destroyed."""

    ...


class ObjectDeletedError(RuntimeError):
    """Raised when accessing a child object after its parent has been deleted."""

    ...


class PluginDescription:
    """Describes an available audio plugin (VST3, AU, or built-in)."""

    @property
    def name(self) -> str:
        """Display name of the plugin."""
        ...

    @property
    def manufacturer(self) -> str:
        """Plugin manufacturer or vendor."""
        ...

    @property
    def identifier(self) -> str:
        """Unique plugin identifier string used with ``Track.insert_plugin()``."""
        ...

    @property
    def format(self) -> str:
        """Plugin format (``"VST3"``, ``"AU"``, or ``"builtin"``)."""
        ...

    @property
    def is_instrument(self) -> bool:
        """Whether this plugin is a virtual instrument (vs. an effect)."""
        ...


class RenderOptions:
    """Configuration for offline audio rendering.

    All fields have sensible defaults; only ``output_path`` is required
    for a successful render.
    """

    output_path: str
    """Filesystem path for the rendered audio file (e.g. ``"out.wav"``)."""

    sample_rate: int
    """Sample rate in Hz (default 44100)."""

    bit_depth: Literal[16, 24, 32]
    """Bit depth for the output file (default 16)."""

    start_seconds: float
    """Render start position in seconds (default 0.0)."""

    end_seconds: float
    """Render end position in seconds (-1.0 means render to end of content)."""

    def __init__(self) -> None: ...


class MidiClip:
    """A MIDI clip on a track, containing note events."""

    def add_note(
        self,
        pitch: int,
        start_beat: float,
        length_beats: float,
        velocity: int = 100,
    ) -> None:
        """Add a single MIDI note to this clip.

        Args:
            pitch: MIDI note number (0-127).
            start_beat: Start position in beats relative to clip start.
            length_beats: Note duration in beats.
            velocity: MIDI velocity (0-127, default 100).
        """
        ...

    def add_notes(
        self,
        notes: Iterable[
            tuple[int, float, float] | tuple[int, float, float, int]
        ],
    ) -> None:
        """Add multiple notes to this clip.

        Each element is ``(pitch, start_beat, length_beats)`` or
        ``(pitch, start_beat, length_beats, velocity)``.  Elements may be
        raw numbers or musical-type objects (``Pitch``, ``Duration``,
        ``Velocity``).

        Args:
            notes: Iterable of 3- or 4-element note tuples.
        """
        ...

    def clear_notes(self) -> None:
        """Remove all notes from this clip."""
        ...

    def get_name(self) -> str:
        """Return the clip name."""
        ...


class AudioClip:
    """An audio clip on a track, referencing an audio file on disk."""

    def get_name(self) -> str:
        """Return the clip name."""
        ...

    def get_file_path(self) -> str:
        """Return the absolute path to the source audio file."""
        ...

    def get_start_beat(self) -> float:
        """Return the clip start position in beats."""
        ...

    def get_length_beats(self) -> float:
        """Return the clip length in beats."""
        ...

    def set_gain(self, linear: float) -> None:
        """Set the clip gain as a linear multiplier.

        Args:
            linear: Gain multiplier (0.0 = silent, 1.0 = unity).
                Use ``dawsmith.gain.db()`` to convert from decibels.
        """
        ...

    def get_gain(self) -> float:
        """Return the current clip gain as a linear multiplier."""
        ...

    def set_loop(self, looping: bool) -> None:
        """Enable or disable looping for this clip."""
        ...

    def get_loop(self) -> bool:
        """Return whether looping is enabled."""
        ...


class Plugin:
    """A loaded audio plugin instance on a track."""

    def get_name(self) -> str:
        """Return the plugin display name."""
        ...

    def get_parameter_count(self) -> int:
        """Return the number of automatable parameters."""
        ...

    def get_parameter_name(self, index: int) -> str:
        """Return the name of a parameter by index.

        Args:
            index: Parameter index (0 to ``get_parameter_count() - 1``).
        """
        ...

    def get_parameter_value(self, index: int) -> float:
        """Return the current normalized value of a parameter (0.0-1.0).

        Args:
            index: Parameter index (0 to ``get_parameter_count() - 1``).
        """
        ...

    def set_parameter_value(self, index: int, value: float) -> None:
        """Set a parameter value.

        Args:
            index: Parameter index (0 to ``get_parameter_count() - 1``).
            value: Normalized value (0.0-1.0).
        """
        ...

    def is_loaded(self) -> bool:
        """Return whether the plugin has loaded successfully."""
        ...


class Track:
    """An audio track in an edit, containing clips and plugins."""

    def get_name(self) -> str:
        """Return the track name."""
        ...

    def insert_midi_clip(
        self, name: str, start_beat: float, length_beats: float
    ) -> MidiClip:
        """Create a MIDI clip on this track.

        Args:
            name: Display name for the clip.
            start_beat: Start position in beats.
            length_beats: Clip length in beats.

        Returns:
            The new ``MidiClip``. Its lifetime is tied to this track.
        """
        ...

    def insert_audio_clip(
        self, name: str, file_path: str, start_beat: float, length_beats: float
    ) -> AudioClip:
        """Create an audio clip on this track from an audio file.

        Args:
            name: Display name for the clip.
            file_path: Path to the source audio file.
            start_beat: Start position in beats.
            length_beats: Clip length in beats.

        Returns:
            The new ``AudioClip``. Its lifetime is tied to this track.
        """
        ...

    def insert_plugin(self, identifier: str) -> Plugin:
        """Load a plugin onto this track.

        Args:
            identifier: Plugin identifier from
                ``PluginDescription.identifier``.

        Returns:
            The loaded ``Plugin``. Its lifetime is tied to this track.
        """
        ...

    def set_volume(self, linear: float) -> None:
        """Set the track volume as a linear multiplier.

        Args:
            linear: Volume multiplier (0.0 = silent, 1.0 = unity).
                Use ``dawsmith.gain.db()`` to convert from decibels.
        """
        ...

    def set_pan(self, pan: float) -> None:
        """Set the stereo pan position.

        Args:
            pan: Pan value (-1.0 = hard left, 0.0 = center, 1.0 = hard right).
        """
        ...

    def set_mute(self, muted: bool) -> None:
        """Mute or unmute this track.

        Args:
            muted: ``True`` to mute, ``False`` to unmute.
        """
        ...


class Edit:
    """A musical arrangement containing tracks, tempo, and transport controls."""

    def insert_audio_track(self, name: str) -> Track:
        """Create a new audio track in this edit.

        Args:
            name: Display name for the track.

        Returns:
            The new ``Track``. Its lifetime is tied to this edit.
        """
        ...

    def set_tempo(self, bpm: float) -> None:
        """Set the edit tempo.

        Args:
            bpm: Tempo in beats per minute.
        """
        ...

    def render(self, options: RenderOptions) -> None:
        """Render the edit to an audio file (offline bounce).

        Args:
            options: Render configuration specifying output path,
                sample rate, bit depth, and time range.
        """
        ...

    def play(self) -> None:
        """Start real-time playback from the current position."""
        ...

    def stop(self) -> None:
        """Stop playback."""
        ...

    def is_playing(self) -> bool:
        """Return whether the edit is currently playing."""
        ...

    def get_position_seconds(self) -> float:
        """Return the current playback position in seconds."""
        ...


class Engine:
    """The top-level DAWsmith engine managing audio I/O and plugin discovery.

    Create via :func:`create_engine`. Only one engine should typically be
    active at a time.
    """

    def create_edit(self, bpm: float = 120.0) -> Edit:
        """Create a new edit (arrangement).

        Args:
            bpm: Initial tempo in beats per minute (default 120).

        Returns:
            A new ``Edit``. The engine must remain alive while the edit
            is in use.
        """
        ...

    def scan_plugins(self, path: str = "") -> None:
        """Scan for available audio plugins (VST3, AU, etc.).

        Args:
            path: Directory to scan. If empty, scans default system
                plugin locations.
        """
        ...

    def get_available_plugins(self) -> list[PluginDescription]:
        """Return descriptions of all discovered plugins after scanning."""
        ...


def create_engine(app_name: str = "DAWsmith") -> Engine:
    """Create a new DAWsmith engine instance.

    This is the main entry point for the library. The engine manages
    audio I/O, plugin hosting, and edit lifecycle.

    Args:
        app_name: Application name used for plugin hosting
            (default ``"DAWsmith"``).

    Returns:
        A new ``Engine`` instance.
    """
    ...
