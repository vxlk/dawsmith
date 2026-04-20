#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── Colors ──────────────────────────────────────────────────────────────────
red()   { printf '\033[1;31m%s\033[0m\n' "$*"; }
green() { printf '\033[1;32m%s\033[0m\n' "$*"; }
cyan()  { printf '\033[1;36m%s\033[0m\n' "$*"; }

# ── Commands ────────────────────────────────────────────────────────────────

cmd_build() {
    cyan "Building dawsmith (editable install, Release)..."
    pip install --no-build-isolation -e ".[dev]"
}

cmd_debug() {
    cyan "Building dawsmith (editable install, Debug — full symbols, no optimization)..."
    pip install --no-build-isolation -e ".[dev]" \
        -C cmake.define.CMAKE_BUILD_TYPE=Debug
}

cmd_install() {
    cyan "Installing dawsmith from source..."
    pip install ".[dev]"
}

cmd_test() {
    cyan "Running tests..."
    python -m pytest tests/ "$@"
}

cmd_lint() {
    cyan "Linting Python (ruff)..."
    python -m ruff check src/ tests/ examples/
    cyan "Linting C++ (clang-format --dry-run)..."
    find src/cpp -name '*.cpp' -o -name '*.h' | while read -r f; do
        clang-format --dry-run --Werror "$f" 2>&1 && true
    done
    green "Lint passed."
}

cmd_fmt() {
    cyan "Formatting Python (ruff)..."
    python -m ruff format src/ tests/ examples/
    python -m ruff check --fix src/ tests/ examples/ || true
    cyan "Formatting C++ (clang-format)..."
    find src/cpp -name '*.cpp' -o -name '*.h' | xargs clang-format -i
    green "Formatted."
}

cmd_check() {
    cyan "Running all checks (fmt --check + lint + test)..."
    python -m ruff format --check src/ tests/ examples/
    python -m ruff check src/ tests/ examples/
    find src/cpp -name '*.cpp' -o -name '*.h' | while read -r f; do
        clang-format --dry-run --Werror "$f"
    done
    python -m pytest tests/ "$@"
    green "All checks passed."
}

cmd_clean() {
    cyan "Cleaning build artifacts..."
    rm -rf build/ dist/ *.egg-info _skbuild/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    green "Clean."
}

cmd_help() {
    cat <<EOF
$(cyan "dawsmith dev.sh")

Usage: ./dev.sh <command> [args...]

Commands:
  build     Editable install (pip install -e) with native rebuild (Release)
  debug     Editable install with full debug symbols and no optimization
  install   Full install from source
  test      Run pytest (extra args forwarded, e.g. ./dev.sh test -k chord)
  lint      Check Python (ruff) and C++ (clang-format) without modifying files
  fmt       Auto-format Python (ruff) and C++ (clang-format) in place
  check     Run fmt --check + lint + tests (CI-style gate)
  clean     Remove build artifacts and __pycache__ dirs
  help      Show this message
EOF
}

# ── Dispatch ────────────────────────────────────────────────────────────────

case "${1:-help}" in
    build)   shift; cmd_build "$@" ;;
    debug)   shift; cmd_debug "$@" ;;
    install) shift; cmd_install "$@" ;;
    test)    shift; cmd_test "$@" ;;
    lint)    shift; cmd_lint "$@" ;;
    fmt)     shift; cmd_fmt "$@" ;;
    check)   shift; cmd_check "$@" ;;
    clean)   shift; cmd_clean "$@" ;;
    help|-h|--help) cmd_help ;;
    *)
        red "Unknown command: $1"
        cmd_help
        exit 1
        ;;
esac
