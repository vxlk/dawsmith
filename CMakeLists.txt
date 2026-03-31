cmake_minimum_required(VERSION 3.15...3.27)
project(dawsmith LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# --- MSVC static runtime (matches Tracktion examples) ---
if (MSVC)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()

# --- Python + nanobind ---
if (CMAKE_VERSION VERSION_LESS 3.18)
    set(DEV_MODULE Development)
else()
    set(DEV_MODULE Development.Module)
endif()
find_package(Python 3.10 COMPONENTS Interpreter ${DEV_MODULE} REQUIRED)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
    OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE nanobind_ROOT)
find_package(nanobind CONFIG REQUIRED)

# --- Fetch Tracktion Engine (includes JUCE as git submodule) ---
include(FetchContent)
set(TE_ADD_EXAMPLES OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
    tracktion_engine
    GIT_REPOSITORY https://github.com/Tracktion/tracktion_engine.git
    GIT_TAG        v3.2.0
    GIT_SHALLOW    TRUE
)
# Use EXCLUDE_FROM_ALL so only targets we depend on are built (not TE examples)
FetchContent_GetProperties(tracktion_engine)
if(NOT tracktion_engine_POPULATED)
    FetchContent_Populate(tracktion_engine)
    add_subdirectory(${tracktion_engine_SOURCE_DIR} ${tracktion_engine_BINARY_DIR} EXCLUDE_FROM_ALL)
endif()

# --- Build the nanobind Python extension ---
nanobind_add_module(_native NB_STATIC
    src/cpp/python_bindings.cpp
    src/cpp/tracktion_backend.cpp
)

target_include_directories(_native PRIVATE src/cpp)

target_link_libraries(_native PRIVATE
    tracktion::tracktion_core
    tracktion::tracktion_engine
    tracktion::tracktion_graph
    juce::juce_audio_devices
    juce::juce_audio_processors
    juce::juce_audio_utils
)

target_compile_definitions(_native PRIVATE
    JUCE_PLUGINHOST_VST3=1
    JUCE_USE_CURL=0
    JUCE_WEB_BROWSER=0
    JUCE_MODAL_LOOPS_PERMITTED=1
    JUCE_STRICT_REFCOUNTEDPOINTER=1
    JUCE_APPLICATION_NAME_STRING="DAWsmith"
    JUCE_APPLICATION_VERSION_STRING="0.1.0"
)

install(TARGETS _native LIBRARY DESTINATION dawsmith)
