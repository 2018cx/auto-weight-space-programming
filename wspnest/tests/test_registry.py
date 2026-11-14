import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wspnest.registry import all_tasks, load_task, load_release


def test_all_tasks_valid():
    for t in all_tasks():
        _, errs = load_task(t)
        assert not errs, errs


def test_frontier_release_pins_existing_versions():
    _, errs = load_release("frontier")
    assert not errs, errs


def test_hide_numbers():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks", "logit-lens-4way", "scorer"))
    import score
    p = "Intro.\n\n[0] 1 2 3\n[64] 4 5 6\n\nRead these weights."
    assert score.hide_numbers(p) == "Intro.\n\n(numbers hidden)\n\nRead these weights."
