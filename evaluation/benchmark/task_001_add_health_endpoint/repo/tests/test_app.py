def test_placeholder_passes():
    """Deliberately does not import app.py — pytest's default import mode
    would insert this file's own directory onto sys.path, not the repo
    root, so an `from app import ...` here would fail for path reasons
    unrelated to what this benchmark is actually testing. See
    task_001's expected_behavior.md for what this benchmark measures.
    """
    assert True
