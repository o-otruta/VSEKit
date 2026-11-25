"""Reference-video breakdown (run with VENV_PY): editing pace, speech, loudness, structure.

    python -m vsekit.analyze <url-or-file> [out_dir]
"""
import json
import os
import sys

from . import media as M, scenes as S, transcribe as T
from .env import MEDIA


def _fmt(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def analyze(src, out_dir=None):
    meta = {}
    if src.startswith("http"):
        from . import download as D
        meta = D.info(src)
        out_dir = out_dir or os.path.join(MEDIA, "analysis", meta["id"])
        D.video(src, out_dir, name="video", subs=False)
        path = os.path.join(out_dir, "video.mp4")
    else:
        path = src
        out_dir = out_dir or os.path.join(os.path.dirname(src), os.path.splitext(os.path.basename(src))[0] + "_analysis")
    os.makedirs(out_dir, exist_ok=True)

    pr = M.probe(path)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    dur = float(pr["format"]["duration"])
    sc = S.detect(path)
    st = S.stats(sc)
    tr = T.transcribe(path)
    ws = T.words(tr)
    speech = sum(w["end"] - w["start"] for w in ws)
    loud = M.loudness(path)
    M.contact_sheet(path, os.path.join(out_dir, "contact.png"), every_s=max(1.0, dur / 48), cols=8, width=240)

    # pacing over time: cuts per 30 s
    buckets = [0] * (int(dur // 30) + 1)
    for s in sc[1:]:
        buckets[int(s["start"] // 30)] += 1
    first_cut = sc[1]["start"] if len(sc) > 1 else dur
    hook_words = " ".join(w["text"] for w in ws if w["start"] < 8)

    lines = [f"# Video breakdown: {meta.get('title', os.path.basename(path))}", ""]
    if meta:
        lines += [f"- Channel: {meta.get('channel')} · views {meta.get('view_count')} · uploaded {meta.get('upload_date')}",
                  f"- License: {meta.get('license') or 'standard (not reusable)'}", ""]
    lines += [
        "## Format",
        f"- {v['width']}x{v['height']} @ {v['r_frame_rate']} · duration {_fmt(dur)}",
        f"- Loudness {loud.get('lufs')} LUFS, true peak {loud.get('true_peak')} dBTP",
        "", "## Editing pace",
        f"- Shots: {st['shots']} · avg {st['avg_shot_s']:.1f}s · median {st['median_shot_s']:.1f}s · {st['cuts_per_min']:.1f} cuts/min",
        f"- First cut at {first_cut:.1f}s",
        "- Cuts per 30 s: " + " ".join(f"[{_fmt(i * 30)}] {n}" for i, n in enumerate(buckets)),
        "", "## Speech",
        f"- Language: {tr['language']} · {len(ws)} words · {len(ws) / (dur / 60):.0f} words/min overall, "
        f"{len(ws) / (speech / 60 + 1e-6):.0f} wpm while talking",
        f"- Talking {100 * speech / dur:.0f}% of runtime",
        f"- Hook (first 8 s): \"{hook_words}\"",
        "", "## Rough chapters (from transcript)",
    ]
    lines += [f"- {_fmt(t)} {txt}" for t, txt in T.chapters(tr, every_s=max(30.0, dur / 8))]
    if meta.get("chapters"):
        lines += ["", "## Author's chapters"] + [f"- {_fmt(c['start_time'])} {c['title']}" for c in meta["chapters"]]
    lines += ["", "![contact sheet](contact.png)", "", "## Transcript", "", T.text(tr)]
    report = os.path.join(out_dir, "report.md")
    open(report, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"scenes": sc, "stats": st, "loudness": loud}, open(os.path.join(out_dir, "data.json"), "w"), indent=1)
    return report


if __name__ == "__main__":
    print(analyze(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
