"""Explicit descriptions of the existing built-in contract, including legacy aliases."""
from __future__ import annotations

from dataclasses import replace

from ..content import (Children, Count, ElementRef, ForbidCommon, NamedCheck, Rule,
                       Needs, Only, Parent, RequireCommon, Sequence, UniqueSlots)
from ..metadata import IdRef, Number, ValidatedText
from ..registry import ComponentRegistry, ComponentSpec


DOCUMENT_RULES = (
    NamedCheck("duplicate-ids", "IDs are unique across the lowered document.", phase="lowering"),
    NamedCheck("navigation-targets", "Navigation and initial switcher IDs name direct switcher children.", phase="references"),
    NamedCheck("document-accelerators", "Declared tab accelerators are unique across the document.", phase="document-final"),
    NamedCheck("data-only-attributes", "Data-only tag names reject common attributes, including autofocus, and events.", phase="lowering"),
    NamedCheck("common-identifiers", "Nonempty IDs and whitespace-separated classes follow native Textual identifier validation.", phase="lowering"),
    NamedCheck("inline-styles", "Inline and linked TCSS follow the native Textual stylesheet parser.", phase="styling"),
)


def _builtin_rules(spec: ComponentSpec) -> tuple[Rule, ...]:
    # Local imports avoid a registry/adapter/loader import cycle.
    from . import structure
    from .bars import SLOT_FACTORIES, build_bar
    from .builtin_widgets import NAV_CHILDREN, SPLIT_CHILDREN, build_nav, build_split
    from .data_widgets import build_cell, build_column, build_data_table, build_row, build_tree, build_tree_node
    from .display_controls import build_progress_bar, build_radio_button, build_radio_set, build_range
    from .form_controls import build_option, build_select
    from .modal import build_modal
    from .tabbed import build_tab_pane, build_tabbed_content

    def ref(tag, factory):
        return ElementRef(tag, factory)

    def named(name, doc, check):
        return NamedCheck(name, doc, check)

    data = ForbidCommon("data-only children accept no common widget attributes or events", events=True)
    option, pane, radio = ref("option", build_option), ref("tab-pane", build_tab_pane), ref("radio-button", build_radio_button)
    column, row, cell = ref("column", build_column), ref("row", build_row), ref("cell", build_cell)
    tree_node = ref("tree-node", build_tree_node)
    rules = {
        build_modal: (Parent(message="modal must be a document root", root_only=True),
                      RequireCommon("id", "modal requires an id")),
        build_option: (Parent((ref("select", build_select),), "option must be a direct child of select"),
                       ForbidCommon("option accepts no common widget attributes")),
        build_select: (Count(minimum=1, message="select requires option children"),
                       Only((option,), "select requires option children"),
                       named("select-values", "Unique option values; initial value names an option.", structure.select_values)),
        build_tab_pane: (Parent((ref("tabbed-content", build_tabbed_content),), "tab-pane must be a direct child of tabbed-content"),
                         RequireCommon("id", "tab-pane requires an id"),
                         Needs("accelerator", "accelerator-scope", "accelerator-scope", "tab-pane accelerator requires accelerator-scope=document"),
                         Needs("accelerator-scope", "accelerator", "accelerator-scope", "accelerator-scope requires an accelerator")),
        build_tabbed_content: (Count(minimum=1, message="tabbed-content requires tab-pane children"),
                               Only((pane,), "tabbed-content requires tab-pane children"),
                               named("initial-tab", "Initial names a direct child pane ID.", structure.initial_tab)),
        build_radio_button: (named("radio-events", "Nested radio buttons declare events on their radio set.", structure.radio_events),),
        build_radio_set: (Count(minimum=1, message="radio-set requires radio-button children"),
                          Only((radio,), "radio-set requires radio-button children"),
                          named("radio-selection", "At most one radio button is selected.", structure.radio_selection)),
        build_progress_bar: (named("progress-bounds", "Progress cannot exceed a declared total.", structure.progress_bounds),),
        build_range: (named("range-bounds", "Ordered bounds, dividing step and aligned value within bounds.", structure.range_bounds),),
        build_column: (Parent((ref("data-table", build_data_table),), "column has an invalid parent"), data),
        build_row: (Parent((ref("data-table", build_data_table),), "row has an invalid parent"), data,
                    Only((cell,), "row accepts only cell children")),
        build_cell: (Parent((row,), "cell has an invalid parent"), data),
        build_tree_node: (Parent((ref("tree", build_tree), tree_node), "tree-node has an invalid parent"), data,
                          Only((tree_node,), "tree accepts only tree-node children")),
        build_data_table: (Only((column, row), "data-table accepts only column and row children"),
                           named("table-requires-columns", "Seeded rows require declared columns.", structure.table_requires_columns),
                           Sequence((column, row), "data-table columns must precede rows"),
                           named("table-keys-and-widths", "Unique column/row keys; cell counts match column count.", structure.table_keys_and_widths)),
        build_tree: (Only((tree_node,), "tree accepts only tree-node children"),
                     named("tree-keys", "Tree-node keys are unique within each tree.", structure.tree_keys)),
        build_split: (SPLIT_CHILDREN,),
        build_nav: (NAV_CHILDREN,),
    }
    if spec.tag in SLOT_FACTORIES and spec.factory is SLOT_FACTORIES[spec.tag]:
        return (Parent((ref("header", build_bar),), "slot must be a direct child of header or status-bar"),)
    if spec.tag in {"header", "status-bar"} and spec.factory is build_bar:
        return (Only(tuple(ElementRef(tag) for tag in SLOT_FACTORIES), f"{spec.tag} accepts only left, center, and right slots"),
                UniqueSlots(f"{spec.tag} accepts each slot at most once"),
                NamedCheck("bar-native-slots", "Slots construct native HeaderSlot instances with unique positions.", phase="build"))
    return next((content for factory, content in rules.items() if spec.factory is factory), ())


def content_for(spec: ComponentSpec) -> Children:
    """Use explicit content or preserve native-factory rules for legacy registrations."""
    return spec.content if spec.content is not None else Children(_builtin_rules(spec), policy=spec.child_policy)


def enrich_builtin_registry(registry: ComponentRegistry) -> ComponentRegistry:
    from .command_button import _command_name
    from .data_widgets import nonempty_key
    from .runtime_list import nonempty_string
    from .tabbed import accelerator

    validators = {
        accelerator: "unicode-alphanumeric-character",
        _command_name: "python-identifier",
        nonempty_key: "nonempty-key",
        nonempty_string: "direct-mapping-format",
    }
    result = ComponentRegistry()
    for spec in registry.snapshot().values():
        attributes = {}
        for name, attribute in spec.attributes.items():
            value_type = attribute.value_type
            if attribute.converter in validators:
                value_type = ValidatedText(validators[attribute.converter], attribute.converter)
            elif spec.tag == "progress-bar" and name in {"total", "progress"}:
                value_type = Number(positive=name == "total")
            elif name == "initial" and spec.tag in {"tabbed-content", "content-switcher"}:
                value_type = IdRef("children")
            elif spec.tag == "nav-item" and name == "target":
                value_type = IdRef("content-switcher-children")
            attributes[name] = replace(attribute, value_type=value_type)
        result.register(replace(spec, attributes=attributes, content=content_for(spec)))
    return result
