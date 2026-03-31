"""DAWsmith -- programmatic music production engine."""

__version__ = "0.1.0"

try:
    from dawsmith._native import (
        create_engine,
        Engine,
        Edit,
        Track,
        MidiClip,
        Plugin,
        PluginDescription,
        RenderOptions,
    )

    __all__ = [
        "create_engine",
        "Engine",
        "Edit",
        "Track",
        "MidiClip",
        "Plugin",
        "PluginDescription",
        "RenderOptions",
    ]
except ImportError as e:
    import warnings
    warnings.warn(
        f"Native module not found: {e}. "
        "Build with 'pip install -e .' to compile C++ bindings.",
        ImportWarning,
        stacklevel=2,
    )
