import subprocess
import sys
from pathlib import Path


def test_new_lesson_creates_a_folder(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    dest = tmp_path / "lessons"
    dest.mkdir()
    (dest / "_template").mkdir()
    (dest / "_template" / "example.py").write_text("print('x')\n")
    subprocess.run(
        [sys.executable, str(repo / "scripts" / "new-lesson.py"),
         "03", "selective-disclosure", "--lessons-dir", str(dest)],
        check=True,
    )
    assert (dest / "03-selective-disclosure" / "example.py").exists()
