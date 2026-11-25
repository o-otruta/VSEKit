"""Storyboard & timing for the ProjectB devlog teaser. Frames are 0-based here (build adds 1)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")
BLEND = os.path.join(HERE, "projectb_devlog.blend")

KIT = os.path.dirname(os.path.dirname(HERE))
PB = os.environ.get("PROJECTB_ROOT", r"D:\UnityProjects\ProjectB")   # game repo: screenshots + voxel models
SHOTS = os.path.join(PB, "Screenshots")
MODELS = os.path.join(PB, "ArtSources", "Blender")
FONT_TITLE = os.path.join(KIT, "assets", "fonts", "RussoOne-Regular.ttf")
FONT_BODY = os.path.join(KIT, "assets", "fonts", "Rubik-Bold.ttf")

W, H, FPS = 1080, 1920, 30
BPM = 120
BEAT = FPS * 60 // BPM          # 15 frames
TOTAL = 1050                    # 35 s

YELLOW = (1.0, 0.84, 0.04)
SEC = {
    "intro":   (0, 120),
    "hook":    (120, 300),
    "ba":      (300, 480),
    "montage": (480, 660),
    "boss":    (660, 780),
    "adapt":   (780, 930),
    "outro":   (930, TOTAL),
}
SLAM = 712                      # boss slam moment (after speed-ramp), see build.py

VO = [  # id, start frame, text
    ("vo1", 128, "I'm building a voxel survivor game. Solo."),
    ("vo2", 228, "Here's what changed this month."),
    ("vo3", 306, "The old UI looked like a prototype. So I rebuilt every screen."),
    ("vo4", 486, "Twenty-seven abilities. Twelve synergies. Fifty-nine achievements."),
    ("vo5", 668, "And a Demon Lord waiting at wave one hundred."),
    ("vo6", 792, "Portrait on phones. Landscape on the web."),
    ("vo7", 940, "Follow, and watch it ship."),
]
VOICE = "en-US-AndrewMultilingualNeural"
VOICE_RATE = "+4%"

CAPTION_Y = {"default": 1250, "adapt": 1010}

MONTAGE = [  # 6 cuts x 30 frames, beat-synced
    "Sprint13/after_levelup_9x16.png",
    "Sprint13/after_abilities_9x16.png",
    "Sprint13/after_constellation_9x16.png",
    "Sprint13/after_upgrades_9x16.png",
    "Sprint13/after_achievements_9x16.png",
    "Sprint13/after_gameover_9x16.png",
]
COUNTERS = [(482, 27, "ABILITIES"), (542, 12, "SYNERGIES"), (602, 59, "ACHIEVEMENTS")]

HOOK_BG = "Sprint14/hud_9x16.png"
BEFORE = "Sprint13/before_hud.png"
AFTER = "Sprint14/hud_9x16.png"
LANDSCAPE = "Sprint14/hud_16x9.png"
PORTRAIT = "Sprint14/hud_9x16.png"
