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
