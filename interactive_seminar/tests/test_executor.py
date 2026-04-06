from interactive_seminar.executor import (
    apply_assignment_overrides,
    execute_block,
    sanitize_cell_source,
)
from interactive_seminar.notebook_loader import load_manifest


class FakeRunner:
    def run(
        self,
        *,
        credentials,
        model,
        prompt_or_messages,
        system_prompt='',
        prefill='',
        stop_sequences=None,
    ):
        if prompt_or_messages == 'Count to 3.':
            return '1 2 3'
        return 'unhandled'


def test_sanitize_cell_source_removes_ipython_magics():
    source = '%store -r MODEL_NAME\nprint(MODEL_NAME)\n'
    assert sanitize_cell_source(source) == 'print(MODEL_NAME)\n'


def test_apply_assignment_overrides_replaces_prompt_assignment_only():
    source = 'PROMPT = "[Replace this text]"\nresponse = get_completion(PROMPT)\n'
    updated = apply_assignment_overrides(source, {'PROMPT': 'Count to 3.'})
    assert 'PROMPT = "Count to 3."' in updated
    assert 'response = get_completion(PROMPT)' in updated


def test_execute_graded_block_returns_grade():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('exercise-1-1-counting-to-three')

    result = execute_block(
        block,
        {'PROMPT': 'Count to 3.'},
        FakeRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert result.response == '1 2 3'
    assert result.grade.passed is True
