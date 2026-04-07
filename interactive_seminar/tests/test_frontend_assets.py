from pathlib import Path


def test_hint_is_rendered_as_collapsible_details():
    app_js = Path('interactive_seminar/static/app.js').read_text()
    assert '<details class="hint-card">' in app_js
    assert '<summary>Hint</summary>' in app_js


def test_context_fields_are_rendered_as_editable_textareas():
    app_js = Path('interactive_seminar/static/app.js').read_text()
    assert 'Context Fields' in app_js
    assert 'field-type">context</span>' in app_js
    assert 'Read-only Context' not in app_js
