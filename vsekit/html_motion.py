"""HTML/CSS/SVG motion graphics -> deterministic PNG sequence (with alpha) for a VSE image strip.

Why: per-glyph kinetic type, SVG line drawing, UI mockups, d3 charts and Lottie are cheap in a browser
and painful in Blender. This renders them frame by frame by *seeking* time (never by recording real-time
playback), so every frame exists, renders are repeatable and transparent areas stay transparent.

Authoring contract for the HTML page:
- Animate with CSS animations/transitions or the Web Animations API — they are seeked automatically
  (`document.getAnimations()`, currentTime = t). Anything else (canvas, GSAP, lottie-web, d3 timers)
  must expose `window.seek = (t) => {...}` (t in seconds; may be async) and draw state *from t only*.
- Keep `html, body { background: transparent }` for an overlay; paint a background for a full-frame clip.
- `window.PARAMS` holds the `params` dict (text, colours ...) so one template serves many clips.
- Fonts: families "VSEKit Title" (Russo One) and "VSEKit Body" (Rubik) are pre-registered.

Run with VSEKit/.venv python. Chromium comes from `python -m playwright install chromium --only-shell`.
"""
import json
import os
import pathlib

from .env import FONT_BODY, FONT_TITLE

_INIT = """
window.PARAMS = %s;
window.__vsekitSeek = async (t) => {
  if (typeof window.seek === 'function') { await window.seek(t); }
  for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
};
"""

_FONTS = """
@font-face { font-family: 'VSEKit Title'; src: url('%s'); }
@font-face { font-family: 'VSEKit Body'; src: url('%s'); }
"""


def _uri(p):
    return pathlib.Path(os.path.abspath(p)).as_uri()


def render(html, out_dir, duration, fps=60, width=1920, height=1080, transparent=True, params=None,
           prefix="f_", start=0.0, clean=True):
    """Render `html` (file path) from `start` for `duration` seconds into out_dir/f_0000.png ...
    Frame i shows time start + i/fps; there are round(duration*fps) frames (the end time itself is not a
    frame). Returns the list of PNG paths, ready for `vse.image_seq()`."""
    from playwright.sync_api import sync_playwright

    os.makedirs(out_dir, exist_ok=True)
    if clean:
        for f in os.listdir(out_dir):
            if f.startswith(prefix) and f.endswith(".png"):
                os.remove(os.path.join(out_dir, f))
    n = round(duration * fps)
    files = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.add_init_script(_INIT % json.dumps(params or {}))
        page.goto(_uri(html))
        page.add_style_tag(content=_FONTS % (_uri(FONT_TITLE), _uri(FONT_BODY)))
        page.evaluate("document.fonts.ready.then(() => true)")
        page.evaluate("() => Promise.all([...document.fonts].map(f => f.load().catch(() => null)))")
        for i in range(n):
            page.evaluate("t => window.__vsekitSeek(t)", start + i / fps)
            path = os.path.join(out_dir, f"{prefix}{i:04d}.png")
            page.screenshot(path=path, omit_background=transparent)
            files.append(path)
        browser.close()
    return files


def still(html, out_png, t, width=1920, height=1080, transparent=True, params=None):
    """One frame at time t — for checking layout before a full render."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        f = render(html, tmp, 1, fps=1, width=width, height=height, transparent=transparent, params=params,
                   start=t)[0]
        shutil.copy(f, out_png)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out_png
