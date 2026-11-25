# VSEKit

Scripted, but fully editable video editing on top of **Blender's Video Sequencer**, plus a local AI/ffmpeg
toolbox. Scripts produce a normal `.blend` (named channels, strips, keyframes, compositor node groups) that
you open, tweak by hand and re-render. The Claude Code skill in `skill/video-editing` tells Claude how to
use (and extend) all of it.

## Install on a new machine (Windows)

```powershell
git clone <this repo> $HOME\Documents\VSEKit      # any folder works
cd $HOME\Documents\VSEKit
powershell -ExecutionPolicy Bypass -File setup.ps1          # full (several GB: torch, models download later)
# or: setup.ps1 -SkipML                                      # light: no torch/whisper/kokoro/DeepFilterNet
.venv\Scripts\python.exe tools\doctor.py                    # re-check any time
```

`setup.ps1` is idempotent. It sets `VSEKIT_ROOT`, installs ffmpeg / deno / uv (and Blender if none is
found) via winget, creates `.venv` (Python 3.12; CUDA torch when an NVIDIA GPU is present) and `.venv-df`
(DeepFilterNet), downloads Real-ESRGAN, installs Pillow + edge-tts into Blender's user modules and links the
skill into `%USERPROFILE%\.claude\skills\video-editing` (junction → updating the repo updates the skill).

Manual, optional: the Blender MCP extension (lets Claude drive the open Blender UI) and, for game capture,
Unity MCP + `com.unity.recorder` in the Unity project. Demo source media: `demos\fetch_media.py`.
Whisper / Kokoro models download on first use (~2 GB, Hugging Face cache).

Overrides if auto-detection picks the wrong thing: `VSEKIT_BLENDER`, `VSEKIT_FFMPEG_DIR`, `VSEKIT_DENO`,
`VSEKIT_ROOT`; game assets for the ProjectB demos: `PROJECTB_ROOT`. Check with `python -m vsekit.env`.

## Layout

| Path | What |
|---|---|
| `vsekit/` | the library (see below) |
| `skill/video-editing/` | Claude Code skill: workflow, tool verdicts, API pitfalls, platform specs |
| `projects/<name>/` | one folder per real video: `config.py` → `prepare.py` → `build.py` → `make.sh` |
| `demos/` | one script per tool test; outputs in `demos/out/` (gitignored) |
| `tools/` | `doctor.py`, Unity editor scripts (`tools/unity/`), downloaded binaries (gitignored) |
| `assets/fonts/` | Russo One + Rubik (SIL OFL, licences included) |
| `media/` | downloads, recordings, analysis (gitignored) |

## Library (`vsekit/`)

Outside Blender (`.venv`): `env` (tool discovery), `audio` (music/SFX synth), `gfx` (Pillow graphics),
`tts` (edge / kokoro / sapi + whisper align), `media` (ffmpeg: probe, loudness, finalize −14 LUFS, contact
sheets, image-sequence assembly), `transcribe` (whisper, SRT, jump-cut lists, chapters), `beats` (tempo,
beats, downbeats, energy), `scenes` (shot detection), `denoise` (DeepFilterNet, ffmpeg voice chain,
silencedetect), `upscale` (Real-ESRGAN), `download` (yt-dlp), `analyze` (`python -m vsekit.analyze
<url|file>` → report.md).

Inside Blender: `vse` (strips, trimmed clips, keys with easing, shake, meta, fades), `fx` (compositor
groups: grade, whip, glitch, iris, CA pulse), `three_d` (voxel models, stop-motion, 3D text, particles),
`preview.py` (frames + contact sheet).

## Tools

| Tool | Installed by | Used via |
|---|---|---|
| Blender 5.x | existing install / winget | timelines, 3D, render |
| ffmpeg (Gyan.FFmpeg) | winget | `vsekit.media` (NVENC when available) |
| deno | winget | yt-dlp's JS runtime for YouTube |
| uv | winget | venv management |
| yt-dlp, faster-whisper, librosa, PySceneDetect, Kokoro, OpenTimelineIO, Pillow, edge-tts | `requirements.txt` → `.venv` | `vsekit.*` |
| torch / torchaudio | setup.ps1 (CUDA or CPU) | whisper, kokoro |
| DeepFilterNet | `requirements-df.txt` → `.venv-df` | `vsekit.denoise` |
| Real-ESRGAN ncnn-vulkan | setup.ps1 download | `vsekit.upscale` |
| Unity Recorder | manual, per Unity project | `tools/unity/record_bot_gameplay.cs` |

## Extending

New reusable code → `vsekit/`; new tool → `setup.ps1` + `requirements*.txt` + `vsekit/env.py` +
`tools/doctor.py` + the table above + a verdict in the skill. No machine-specific paths in code.
Conventional Commits (`feat(scope): …`, `fix(scope): …`, `docs(skill): …`).

**Rebuilding a .blend overwrites manual edits** — script while the structure changes, then polish by hand
(or through the Blender MCP on the open file).
