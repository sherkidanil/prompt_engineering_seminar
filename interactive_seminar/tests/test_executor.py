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


class EchoRunner:
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
        return str(prompt_or_messages)


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


def test_execute_graded_block_accepts_unquoted_raw_string_override():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('exercise-1-1-counting-to-three')

    result = execute_block(
        block,
        {'PROMPT': {'__raw__': 'Count to 3.'}},
        FakeRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert result.prompt_preview == 'Count to 3.'
    assert result.response == '1 2 3'
    assert result.grade.passed is True


def test_execute_open_block_returns_compiled_prompt():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('exercise-9-2-codebot')

    result = execute_block(
        block,
        {'TASK_CONTEXT': 'You are Codebot.'},
        FakeRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert 'You are Codebot.' in result.prompt_preview
    assert result.grade is None


def test_execute_generic_example_uses_messages_as_prompt_preview_and_prereqs():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('part-10-example-2')

    result = execute_block(
        block,
        {},
        EchoRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert 'Please find replacements' in result.prompt_preview
    assert 'Name ten words' in result.prompt_preview
    assert 'Please find replacements' in result.response


def test_execute_block_allows_context_field_overrides():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('part-4-example-1')

    result = execute_block(
        block,
        {'ANIMAL': {'__raw__': '"Dog"'}},
        EchoRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert 'Dog' in result.prompt_preview
    assert 'Dog' in result.response


def test_execute_single_example_bootstraps_notebook_chat_symbols():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('part-1-example-1')

    result = execute_block(
        block,
        {
            'PROMPT': {'__raw__': '"Hi GigaChat, how are you?"'},
            'SYSTEM_PROMPT': {'__raw__': '""'},
        },
        FakeRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert 'NameError' not in result.stdout
    assert result.stdout.strip() == 'unhandled'
    assert result.response == 'unhandled'


class FakeToolRunner:
    def __init__(self):
        self.calls = 0

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
        self.calls += 1
        if self.calls == 1:
            return (
                '<function_calls><invoke name="calculator">'
                '<antml:parameter name="first_operand">2</parameter>'
                '<antml:parameter name="second_operand">6</parameter>'
                '<antml:parameter name="operator">*</parameter>'
                '</invoke>'
            )
        return '12'



def test_find_parameter_extracts_tool_arguments():
    from interactive_seminar.executor import find_parameter

    message = (
        '<function_calls><invoke name="calculator">'
        '<antml:parameter name="first_operand">2</parameter></invoke>'
    )
    assert find_parameter(message, 'first_operand') == '2'



def test_construct_successful_function_run_injection_prompt_formats_results():
    from interactive_seminar.executor import construct_successful_function_run_injection_prompt

    prompt = construct_successful_function_run_injection_prompt([
        {'tool_name': 'calculator', 'tool_result': 12}
    ])
    assert '<function_results>' in prompt
    assert '<tool_name>calculator</tool_name>' in prompt
    assert '<stdout>\n12\n</stdout>' in prompt



def test_execute_tool_use_demo_returns_intermediate_trace():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('tool-use-calculator-demo')

    result = execute_block(
        block,
        {},
        FakeToolRunner(),
        credentials='test-key',
        model='GigaChat',
    )

    assert result.tool_trace['first_response'].startswith('<function_calls>')
    assert result.tool_trace['function_results'].startswith('<function_results>')
    assert result.response == '12'
