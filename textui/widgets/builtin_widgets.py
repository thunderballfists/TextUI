from textual.containers import Center, Container, Grid, Horizontal, HorizontalScroll, Middle, Vertical, \
    VerticalScroll
from textual.widgets import Button, Checkbox, ContentSwitcher, DataTable, DirectoryTree, Footer, Header, Input, Label, \
    ListItem, ListView, LoadingIndicator, Markdown, MarkdownViewer, OptionList, Placeholder, Pretty, RadioButton, \
    RadioSet, Static, Switch, TabbedContent, TabPane, Tab, Tabs, Log, Tree, Welcome

from ..defs.element_widget_definition import ElementWidgetDefinition

BUILT_IN_WIDGETS = [
    ElementWidgetDefinition(tag="center", widget_class=Center),
    ElementWidgetDefinition(tag="container", widget_class=Container),
    ElementWidgetDefinition(tag="grid", widget_class=Grid),
    ElementWidgetDefinition(tag="horizontal", widget_class=Horizontal),
    ElementWidgetDefinition(tag="horizontal_scroll", widget_class=HorizontalScroll),
    ElementWidgetDefinition(tag="middle", widget_class=Middle),
    ElementWidgetDefinition(tag="vertical", widget_class=Vertical),
    ElementWidgetDefinition(tag="vertical_scroll", widget_class=VerticalScroll),
    ElementWidgetDefinition(tag="button", widget_class=Button),
    ElementWidgetDefinition(tag="checkbox", widget_class=Checkbox),
    ElementWidgetDefinition(tag="content_switcher", widget_class=ContentSwitcher),
    ElementWidgetDefinition(tag="data_table", widget_class=DataTable),
    ElementWidgetDefinition(tag="directory_tree", widget_class=DirectoryTree),
    ElementWidgetDefinition(tag="footer", widget_class=Footer),
    ElementWidgetDefinition(tag="header", widget_class=Header),
    ElementWidgetDefinition(tag="input", widget_class=Input),
    ElementWidgetDefinition(tag="label", widget_class=Label),
    ElementWidgetDefinition(tag="list_item", widget_class=ListItem),
    ElementWidgetDefinition(tag="list_view", widget_class=ListView),
    ElementWidgetDefinition(tag="loading_indicator", widget_class=LoadingIndicator),
    ElementWidgetDefinition(tag="markdown", widget_class=Markdown),
    ElementWidgetDefinition(tag="markdown_viewer", widget_class=MarkdownViewer),
    ElementWidgetDefinition(tag="option_list", widget_class=OptionList),
    ElementWidgetDefinition(tag="placeholder", widget_class=Placeholder),
    ElementWidgetDefinition(tag="pretty", widget_class=Pretty),
    ElementWidgetDefinition(tag="radio_button", widget_class=RadioButton),
    ElementWidgetDefinition(tag="radio_set", widget_class=RadioSet),
    ElementWidgetDefinition(tag="static", widget_class=Static),
    ElementWidgetDefinition(tag="switch", widget_class=Switch),
    ElementWidgetDefinition(tag="tabbed_content", widget_class=TabbedContent),
    ElementWidgetDefinition(tag="tab_pane", widget_class=TabPane),
    ElementWidgetDefinition(tag="tab", widget_class=Tab),
    ElementWidgetDefinition(tag="tabs", widget_class=Tabs),
    ElementWidgetDefinition(tag="log", widget_class=Log),
    ElementWidgetDefinition(tag="tree", widget_class=Tree),
    ElementWidgetDefinition(tag="welcome", widget_class=Welcome),
]


