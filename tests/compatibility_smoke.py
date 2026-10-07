"""Run existing behavioral probes against a fresh installed wheel, not a checkout.

Usage: python -I /checkout/tests/compatibility_smoke.py {lowest,latest}
This standalone runner is not ordinary pytest collection.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from packaging.requirements import Requirement
from packaging.version import Version

import textui
import textual


PROBES = (
    "test_styles.py::test_native_cascade_host_blocks_specificity_important_and_inline",
    "test_styles.py::test_theme_variables_and_block_local_variables_use_native_context",
    "test_styles.py::test_style_failure_is_source_aware_and_installs_nothing",
    "test_styles.py::test_declared_style_preset_can_be_toggled_without_losing_other_document_styles",
    "test_styles.py::test_focused_compact_controls_keep_content_across_preset_switches",
    "test_styles.py::test_focus_tints_author_backgrounds_without_replacing_them",
    "test_bars.py::test_header_gradient_label_uses_the_background_geometry",
    "test_bars.py::test_gradient_label_respects_cell_width_padding_alignment_and_lines",
    "test_bars.py::test_gradient_follows_live_background_cascade_changes",
    "test_data_widgets.py::test_column_borders_render_between_headers_and_cells",
    "test_data_widgets.py::test_resizable_table_supports_keyboard_and_drag_without_sorting",
    "test_data_widgets.py::test_clicking_a_header_sorts_ascending_then_descending_once_per_click",
    "test_data_widgets.py::test_frozen_column_resize_edge_does_not_move_with_horizontal_scroll",
    "test_data_widgets.py::test_set_rows_keeps_active_runtime_sort_on_refresh",
    "test_data_widgets.py::test_runtime_table_sort_preserves_integer_precision_and_refresh_identity",
    "test_data_widgets.py::test_cell_selection_uses_exact_table_and_native_event",
    "test_log.py::test_log_keeps_grapheme_clusters_intact_across_deltas",
    "test_log.py::test_log_selection_ended_handles_release_outside_the_log",
    "test_log.py::test_log_discards_mouse_selection_when_selected_rows_change",
    "test_log.py::test_log_mouse_selection_uses_scrolled_content_coordinates",
    "test_split.py::test_split_drag_clamps_and_hide_show_restores_size",
    "test_project_app.py::test_resize_hook_uses_terminal_dimensions_with_screen_gutters",
    "test_project_app.py::test_queued_resize_hook_skips_stale_dimensions",
    "test_project_app.py::test_resize_hook_stops_after_exit",
    "test_modal_lifecycle.py::test_modal_reopens_with_visible_click_target_and_restores_focus",
    "test_accelerators.py::test_component_private_tab_accelerator_preserves_public_id_isolation",
    "test_accelerators.py::test_modal_accelerators_follow_active_screen_and_reopening",
    "test_actions.py::test_textui_shutdown_cancels_untargeted_actions_and_marks_context",
    "test_project_app.py::test_project_shutdown_cancels_untargeted_action_and_command",
    "test_project_timers.py::test_completed_timer_workers_are_released_after_twenty_ticks",
    "test_project_timers.py::test_timer_close_releases_active_workers_and_ignores_unrelated_and_late_messages",
    "test_extensions.py::test_typed_custom_component_and_explicit_custom_message_forwarding",
    "test_actions.py::test_existing_host_explicit_forwarding_and_native_handler_both_run",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", choices=("lowest", "latest"))
    policy = parser.parse_args().policy
    if not sys.flags.isolated:
        raise SystemExit("Use python -I to exclude shell/check-out import paths")
    prefix = Path(sys.prefix).resolve()
    for module in (textui, textual):
        origin = Path(module.__file__).resolve()
        if not origin.is_relative_to(prefix):
            raise SystemExit(f"Expected installed wheel/dependencies under {prefix}; {module.__name__} imports from {origin}")
    requirements = [Requirement(value) for value in importlib.metadata.requires("textui-markup") or ()]
    requirement = next(value for value in requirements if value.name == "textual")
    version = Version(importlib.metadata.version("textual"))
    if version not in requirement.specifier:
        raise SystemExit(f"Textual {version} violates wheel requirement {requirement}")
    floors = [Version(spec.version) for spec in requirement.specifier if spec.operator == ">="]
    if policy == "lowest" and (len(floors) != 1 or version != floors[0]):
        raise SystemExit(f"Lowest policy requires the wheel's inclusive Textual floor; got {version}, {requirement}")
    print(json.dumps({
        "policy": policy,
        "python": sys.version.split()[0],
        "textual": str(version),
        "requirement": str(requirement),
        "textui": str(Path(textui.__file__).resolve()),
    }), flush=True)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="textui-compatibility-") as workdir:
        return subprocess.run([
            sys.executable, "-I", "-m", "pytest", "--import-mode=importlib",
            "-c", str(root / "pyproject.toml"), "-q",
            *(str(root / "tests" / probe) for probe in PROBES),
        ], cwd=workdir).returncode


if __name__ == "__main__":
    raise SystemExit(main())
