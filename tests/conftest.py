def pytest_addoption(parser):
    parser.addoption(
        "--interactive",
        action="store_true",
        default=False,
        help="Run tests in interactive mode",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "interactive: mark test as interactive")

