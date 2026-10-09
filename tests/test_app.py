from streamlit.testing.v1 import AppTest


def test_overview_renders_empty_operational_dashboard():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value == "Operations overview"


def test_new_inspection_page_renders():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("New inspection").run()
    assert not at.exception


def test_public_infrastructure_page_renders_without_importing():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Public infrastructure").run()
    assert not at.exception


def test_maintenance_queue_empty_state_renders():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Maintenance queue").run()
    assert not at.exception


def test_data_sources_page_renders():
    at = AppTest.from_file("app.py", default_timeout=60).run()
    at.sidebar.radio[0].set_value("Data sources").run()
    assert not at.exception
