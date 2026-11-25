"""VSEKit: scripted-yet-editable video editing on top of Blender's Video Sequencer.

Modules that run *outside* Blender (any Python with numpy/Pillow):
    audio  - music / SFX synthesis, wav io
    gfx    - Pillow graphics: captions, pills, cards, counters, gradients
    tts    - neural voice-over with per-word timings (edge-tts)
    media  - ffmpeg helpers (convert, loudness, probe, contact sheets, boundary strips, export checks)
    html_motion - HTML/CSS/SVG animation -> deterministic PNG sequence with alpha (Playwright, .venv)
    (+ transcribe, beats, scenes, denoise, upscale, download, analyze — see README)

Modules that run *inside* Blender (bpy):
    vse      - strips, keyframes with easing, shake, meta, channels
    fx       - compositor node-group effects (grade, whip, glitch, iris)
    three_d  - voxel model import, stop-motion poses, 3D text, particles
"""
