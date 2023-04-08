import asyncio
import contextlib

import pytest
from xml.etree.ElementTree import fromstring
from textual.widgets import RadioButton, RadioSet, Tab, Tabs, Static, Header
from textual.containers import Container, Vertical, VerticalScroll, Horizontal

from main import MyApp, parse_element, parse_markup

@pytest.fixture
def interactive(request):
    return request.config.getoption("--interactive")

async def run_app_for_duration(app, duration=0.1, interactive=False):
    if interactive:
        await app.run_async()
    else:
        task = asyncio.create_task(app.run_async())
        await asyncio.sleep(duration)
        app.exit()
        await task

test_cases = [
    {
        "name": "testo",
        "markup": """
<container>
    <style>
        <![CDATA[
        .test {
            background: blue;
        }
        Header {
            background: green;
            color:blue;
        }
        Footer {
            width: 10%;
            background: blue;
        }
        .accent {
            color: red;
        }
        ]]>
    </style>
    <header/>
    <label id="access">Welcome to the sample XML file</label>
    <label class="accent">label with accent styling.</label>
    <label class="test">label with blue styling.</label>
    <button class="accent">This button has the "accent" class, which applies HSL color.</button>
    <button>This button has default styling.</button>
    <footer/>
</container>
"""}
]

@pytest.mark.parametrize("test_case", test_cases, ids=[case["name"] for case in test_cases])
@pytest.mark.asyncio
async def test_markup(capsys, interactive, test_case):
    interactive = True
    my_app = MyApp(test_case["markup"])

    async with my_app.run_test(headless=not interactive, size=(80, 24)):
        # Optionally, save a screenshot
        file_name = f"{test_case['name']}.svg"
        screenshot_filename = my_app.save_screenshot(filename=file_name)
