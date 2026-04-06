from interactive_seminar.notebook_loader import load_manifest


def test_manifest_contains_all_exercises():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    exercise_titles = [
        block.title
        for part in manifest.parts
        for block in part.blocks
        if block.kind.startswith('exercise')
    ]
    assert 'Exercise 1.1 - Counting to Three' in exercise_titles
    assert 'Exercise 10.2.1 - SQL' in exercise_titles
    assert len(exercise_titles) == 20


def test_manifest_marks_graded_exercises_correctly():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    graded_ids = {
        block.id
        for part in manifest.parts
        for block in part.blocks
        if block.kind == 'exercise_graded'
    }
    assert 'exercise-1-1-counting-to-three' in graded_ids
    assert 'exercise-8-1-prospectus-hallucination' in graded_ids


def test_manifest_exposes_part9_scaffold_fields():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('exercise-9-1-financial-services-chatbot')
    editable_names = [field.name for field in block.editable_fields]
    assert editable_names == [
        'TASK_CONTEXT',
        'TONE_CONTEXT',
        'INPUT_DATA',
        'EXAMPLES',
        'TASK_DESCRIPTION',
        'IMMEDIATE_TASK',
        'PRECOGNITION',
        'OUTPUT_FORMATTING',
        'PREFILL',
        'PROMPT',
    ]


def test_manifest_renders_markdown_html():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    block = manifest.block('part-1-example-1')
    assert "<h3>Examples</h3>" in block.instructions_html
    assert "<code>shift+enter</code>" in block.instructions_html


def test_manifest_splits_generic_examples_into_individual_blocks():
    manifest = load_manifest('PE_seminar.ipynb', 'hints.py')
    part_1_titles = [block.title for block in manifest.parts[0].blocks]
    assert 'Part 1 Example 1' in part_1_titles
    assert 'Part 1 Example 2' in part_1_titles
    assert 'Part 1 Example 3' in part_1_titles
    assert 'Part 1 System Prompt Example' in part_1_titles
