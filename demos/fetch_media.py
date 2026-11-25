"""Re-download the demo source media (media/ is not in git). Run with .venv python.
NASA material is generally not copyrighted; the music is CC BY 4.0 (credit Kevin MacLeod, incompetech.com)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsekit import download as D  # noqa: E402
from vsekit.env import MEDIA  # noqa: E402

SRC = os.path.join(MEDIA, "src")
os.makedirs(SRC, exist_ok=True)


def have(name):
    return any(f.startswith(name + ".") for f in os.listdir(SRC))


if not have("nasa_expert"):
    D.video("https://www.youtube.com/watch?v=MDMM9MZNcco", SRC, name="nasa_expert", subs=False)
if not have("nasa_iss"):
    D.video("https://www.youtube.com/watch?v=5GeAORj0Nw0", SRC, name="nasa_iss", subs=False)
if not have("music_upbeat_forever"):
    D.audio("https://www.youtube.com/watch?v=uH2vJXVCi9U", SRC, name="music_upbeat_forever")
if not have("nasa_students"):
    D._run(["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]", "--merge-output-format", "mp4",
            "--download-sections", "*00:02:30-00:04:00", "--force-keyframes-at-cuts",
            "-o", os.path.join(SRC, "nasa_students.%(ext)s"), "https://www.youtube.com/watch?v=V1O7XfcXGTI"])
print("media ready:", sorted(os.listdir(SRC)))
