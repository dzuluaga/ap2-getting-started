import subprocess
import sys
from pathlib import Path


def _make_template(tmp_path):
    dest = tmp_path / "lessons"
    dest.mkdir()
    (dest / "_template").mkdir()
    (dest / "_template" / "example.py").write_text("print('x')\n")
    return dest


def _run(repo, dest):
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / "new-lesson.py"),
         "03", "selective-disclosure", "--lessons-dir", str(dest)],
    )


def test_new_lesson_creates_a_folder(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    dest = _make_template(tmp_path)
    _run(repo, dest).check_returncode()
    assert (dest / "03-selective-disclosure" / "example.py").exists()


def test_new_lesson_refuses_to_clobber_existing(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    dest = _make_template(tmp_path)
    _run(repo, dest).check_returncode()  # first run succeeds
    second = _run(repo, dest)  # second run must fail, not overwrite
    assert second.returncode != 0
