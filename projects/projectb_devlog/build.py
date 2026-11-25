"""Step 2 (inside Blender): build 3D shots + the editable VSE timeline, save projectb_devlog.blend.
Run:  blender -b --factory-startup --python build.py"""
import json
import math
import os
import sys
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import bpy
from mathutils import Vector, Matrix
import config as C
from vsekit import vse as V, fx as X, three_d as T3
for _m in (C, V, X, T3):
    importlib.reload(_m)

man = json.load(open(os.path.join(C.ASSETS, "manifest.json"), encoding="utf-8"))
IMG, AUD = man["img"], man["audio"]
f = lambda t: int(round(t)) + 1          # storyboard frame (0-based) -> Blender frame
report = {}

bpy.ops.wm.read_factory_settings(use_empty=True)
edit = bpy.data.scenes[0]
edit.name = "Edit"


def az(v, deg):
    return Matrix.Rotation(math.radians(deg), 3, 'Z') @ v


def pose_bounds(o):
    zs = [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
    return min(zs), max(zs)


# ================================================================== 3D: intro (knight + 3D title)
def build_intro():
    s = T3.new_scene("3D Intro", C.W, C.H, C.FPS, 120, world_rgb=(0.010, 0.012, 0.030))
    poses = [f"Knight_Walk_0{i}" for i in range(4)]
    objs = T3.append_objects(s, os.path.join(C.MODELS, "Knight.blend"), ["Knight_Idle", *poses, "PreviewCam"])
    pc = objs.pop("PreviewCam")
    front = Vector((pc.location.x, pc.location.y, 0)).normalized()
    bpy.data.objects.remove(pc)
    zmin, zmax = pose_bounds(objs["Knight_Idle"])
    height = zmax - zmin
    tt = T3.empty(s, "Turntable")
    for o in objs.values():
        o.location.z -= zmin
        o.parent = tt
    T3.stop_motion(T3.walk_schedule(1, 120, poses, step=3), objs, 120)
    V.key(tt, "rotation_euler", 1, (0, 0, -0.45), 'SINE', 'EASE_IN_OUT')
    V.key(tt, "rotation_euler", 120, (0, 0, 0.35), 'LINEAR')

    T3.floor(s, "Floor", 40, (0.015, 0.018, 0.035), 0.45)
    tgt = T3.empty(s, "CamTarget", (0, 0, height * 0.55))
    cam = T3.camera(s, "Camera", front * 7.0 + Vector((0, 0, 1.4)), tgt, lens=50)
    V.key(cam, "location", 1, front * 7.0 + Vector((0, 0, 1.4)), 'CUBIC', 'EASE_OUT')
    V.key(cam, "location", 120, front * 4.6 + Vector((0, 0, 1.9)), 'LINEAR')
    V.key(tgt, "location", 1, (0, 0, height * 0.55), 'SINE', 'EASE_IN_OUT')
    V.key(tgt, "location", 60, (0, 0, height * 0.86), 'LINEAR')

    lt = T3.empty(s, "LightTarget", (0, 0, 1.0))
    T3.area_light(s, "Key", az(front, -45) * 4 + Vector((0, 0, 4.5)), lt, (1.0, 0.82, 0.62), 700, 3)
    T3.area_light(s, "Rim", az(front, 160) * 3.5 + Vector((0, 0, 3.0)), lt, (0.3, 0.75, 1.0), 1500, 2)
    T3.area_light(s, "Fill", az(front, 60) * 4 + Vector((0, 0, 1.5)), lt, (0.55, 0.4, 1.0), 200, 3)

    # 3D title on a rig that always faces the camera; the text itself animates locally
    rig = T3.empty(s, "TitleRig", front * 0.9 + Vector((0, 0, height + 0.5)))
    c = rig.constraints.new('TRACK_TO'); c.target = cam; c.track_axis = 'TRACK_Z'; c.up_axis = 'UP_Y'
    tmat = T3.mat_principled("Title Mat", (1.0, 0.72, 0.08), 0.3, 0.2, emit=(1.0, 0.62, 0.05), emit_strength=2.2)
    title = T3.text3d(s, "Title 3D", "PROJECT B", C.FONT_TITLE, size=0.21, extrude=0.06, bevel=0.01, mat=tmat)
    title.parent = rig
    V.key(title, "scale", 1, (0.001,) * 3, 'CONSTANT')
    V.key(title, "scale", 20, (0.001,) * 3, 'BACK', 'EASE_OUT')
    V.key(title, "scale", 44, (1, 1, 1), 'LINEAR')
    V.key(title, "rotation_euler", 20, (math.radians(-85), 0, 0), 'BACK', 'EASE_OUT')
    V.key(title, "rotation_euler", 44, (0, 0, 0), 'LINEAR')
    V.key(title, "location", 20, (0, -0.25, 0), 'BACK', 'EASE_OUT')
    V.key(title, "location", 44, (0, 0, 0), 'LINEAR')
    V.key(title, "location", 120, (0, 0.05, 0), 'LINEAR')

    ember = T3.cube(s, "Ember", 0.06, T3.mat_principled("Ember Mat", (1, 0.5, 0.1), emit=(1.0, 0.55, 0.15), emit_strength=8))
    T3.particles(s, "Embers", 9, 140, ember, -120, 120, 220, z=-0.1, velocity=0.18, brownian=0.08)
    return s


# ================================================================== 3D: boss (Demon Lord + embers + slam burst)
SLOW_A, SLOW_B, SLOW_TO = 29, 49, 69     # content frames 29..49 stretched to 29..69 (0.5x)
SLAM_CONTENT = 41


def build_boss(front):
    s = T3.new_scene("3D Boss", C.W, C.H, C.FPS, 100, world_rgb=(0.006, 0.003, 0.006))
    names = ["DemonLord_Idle", "DemonLord_Cast", "DemonLord_Charge"]
    objs = T3.append_objects(s, os.path.join(C.MODELS, "DemonLord.blend"), names)
    zmin, zmax = pose_bounds(objs["DemonLord_Idle"])
    height = zmax - zmin
    rig = T3.empty(s, "BossRig")
    for o in objs.values():
        o.location.z -= zmin
        o.parent = rig
    T3.stop_motion([(1, "DemonLord_Idle"), (SLAM_CONTENT, "DemonLord_Cast"), (72, "DemonLord_Charge")], objs, 100)
    V.key(rig, "rotation_euler", 1, (0, 0, -0.3), 'SINE', 'EASE_IN_OUT')
    V.key(rig, "rotation_euler", 100, (0, 0, 0.12), 'LINEAR')

    T3.floor(s, "Floor", 40, (0.03, 0.008, 0.01), 0.35)
    tgt = T3.empty(s, "CamTarget", (0, 0, height * 0.55))
    cam = T3.camera(s, "Camera", front * 10 + Vector((0, 0, 0.5)), tgt, lens=35)
    V.key(cam, "location", 1, front * 10 + Vector((0, 0, 0.5)), 'QUAD', 'EASE_IN')
    V.key(cam, "location", SLAM_CONTENT, front * 5.0 + Vector((0, 0, 0.7)), 'SINE', 'EASE_OUT')
    V.key(cam, "location", 100, front * 4.2 + Vector((0, 0, 0.85)), 'LINEAR')
    V.key(tgt, "location", 1, (0, 0, height * 0.5), 'SINE', 'EASE_IN_OUT')
    V.key(tgt, "location", 100, (0, 0, height * 0.66), 'LINEAR')

    lt = T3.empty(s, "LightTarget", (0, 0, height * 0.5))
    T3.area_light(s, "Key Red", az(front, -35) * 3 + Vector((0, 0, 0.6)), lt, (1.0, 0.1, 0.03), 650, 1.5)
    T3.area_light(s, "Fill Warm", az(front, 25) * 4 + Vector((0, 0, 2.2)), lt, (1.0, 0.85, 0.75), 280, 3)
    T3.area_light(s, "Rim Purple", az(front, 170) * 3 + Vector((0, 0, 3.2)), lt, (0.55, 0.15, 1.0), 2500, 2)
    T3.area_light(s, "Top", Vector((0, 0, 6)) + front * 1.5, lt, (1.0, 0.9, 0.85), 120, 3)

    em = T3.mat_principled("Ember Boss Mat", (1, 0.3, 0.05), emit=(1.0, 0.35, 0.05), emit_strength=12)
    ember = T3.cube(s, "Ember Boss", 0.045, em)
    T3.particles(s, "Embers", 10, 420, ember, -100, 100, 160, z=-0.1, velocity=0.55, brownian=0.5, seed=4)
    debris = T3.cube(s, "Debris", 0.09, T3.mat_principled("Debris Mat", (0.12, 0.05, 0.05), 0.8, emit=(1, 0.25, 0.05), emit_strength=3))
    T3.particles(s, "Slam Burst", 1.4, 140, debris, SLAM_CONTENT, SLAM_CONTENT + 2, 45, z=0.05,
                 velocity=3.2, gravity=1.0, brownian=0.0, seed=9)
    return s


intro = build_intro()
# reuse the knight's "front" so both models face camera the same way
_front = None
for o in intro.objects:
    if o.name == "Camera":
        _front = Vector((o.location.x, o.location.y, 0)).normalized()
boss = build_boss(_front)

# ================================================================== VSE timeline
ed = V.setup(edit, C.W, C.H, C.FPS, C.TOTAL)
try:
    edit.render.compositor_device = 'GPU'
except Exception:
    pass
V.name_channels(ed, {1: "Background / 3D", 2: "Overlay", 3: "Cards", 4: "Graphics", 5: "Titles",
                     6: "Transitions", 7: "Camera FX", 8: "Flash / Dip", 9: "Captions", 10: "Progress track",
                     11: "Progress bar", 12: "Grade", 13: "Voice-over", 14: "Music", 15: "SFX 1", 16: "SFX 2",
                     17: "SFX 3"})
FT, FB = C.FONT_TITLE, C.FONT_BODY
YEL4 = (*C.YELLOW, 1)

# ---------- INTRO
s_in = ed.strips.new_scene("Intro 3D (Knight)", intro, 1, f(0))
s_in.frame_final_end = f(120)

# ---------- HOOK
bg = V.image(ed, "Hook BG", IMG["hook_bg.png"], 1, f(120), f(300), 540, 960)
V.anim_scale(bg.transform, [(f(120), 1.0), (f(300), 1.12)], 'LINEAR')
bd = V.image(ed, "Badge DEVLOG #1", IMG["badge_devlog.png"], 4, f(126), f(298), 540, 330)
V.anim_scale(bd.transform, [(f(126), 0.2), (f(138), 1.0)], 'BACK', 'EASE_OUT')
V.fade(bd, f(126), f(130)); V.fade(bd, f(288), f(297), 1, 0)

imp = V.adjustment(ed, "Impact punch+shake", 7, f(120), f(150))
imp.transform.scale_x = imp.transform.scale_y = 1.0
V.anim_scale(imp.transform, [(f(120), 1.16), (f(132), 1.03), (f(150), 1.0)], 'EXPO', 'EASE_OUT')
V.shake(imp.transform, f(120), f(150), strength=26, speed=1.4, seed=1)
for t in (180, 240):
    p = V.adjustment(ed, f"Beat punch {t}", 7, f(t), f(t + 8))
    V.anim_scale(p.transform, [(f(t), 1.06), (f(t + 8), 1.0)], 'CUBIC', 'EASE_OUT')
fl = V.color(ed, "Flash impact", (1, 1, 1), 8, f(120), f(124))
V.keys(fl, "blend_alpha", [(f(120), 1.0), (f(123), 0.0)], 'LINEAR')

# ---------- BEFORE / AFTER slider
g1 = V.adjustment(ed, "Glitch hook->BA", 6, f(293), f(307))
X.attach(g1, X.glitch("FX Glitch 1", f(293), f(307), seed=3))
V.image(ed, "Before (old UI)", IMG["before.png"], 1, f(300), f(480), 540, 960)
af = V.image(ed, "After (new UI)", IMG["after.png"], 2, f(300), f(480), 540, 960)
for fr, v, it in ((f(300), 1080, 'CONSTANT'), (f(312), 1080, 'CUBIC'), (f(352), 540, 'CONSTANT'),
                  (f(418), 540, 'CUBIC'), (f(446), 0, 'LINEAR')):
    V.key(af.crop, "min_x", fr, v, it, 'EASE_IN_OUT')
dv = V.image(ed, "Slider divider", IMG["divider.png"], 3, f(310), f(452), 1080, 960)
for fr, x, it in ((f(312), 1080, 'CUBIC'), (f(352), 540, 'CONSTANT'), (f(418), 540, 'CUBIC'), (f(446), 0, 'LINEAR')):
    V.key(dv.transform, "offset_x", fr, V.ox(x), it, 'EASE_IN_OUT')
V.fade(dv, f(444), f(451), 1, 0)
lb = V.text(ed, "Label BEFORE", "BEFORE", 5, f(314), f(448), 190, 330, FT, 62, (1, 1, 1, 1), box=(0, 0, 0, 0.62), box_margin=0.012)
la = V.text(ed, "Label AFTER", "AFTER", 4, f(314), f(470), 890, 330, FT, 62, (0.08, 0.06, 0.15, 1), box=YEL4[:3] + (0.95,), box_margin=0.012, shadow=False)
for s_ in (lb, la):
    V.fade(s_, f(314), f(322))
V.fade(lb, f(440), f(447), 1, 0)

# ---------- MONTAGE (beat-synced cuts + whips + counters)
for i in range(6):
    t0 = 480 + 30 * i
    m = V.image(ed, f"Montage {i + 1}", IMG[f"montage_{i}.png"], 1, f(t0), f(t0 + 30), 540, 960)
    V.key(m.transform, "scale_x", f(t0), 1.14, 'CUBIC', 'EASE_OUT'); V.key(m.transform, "scale_y", f(t0), 1.14, 'CUBIC', 'EASE_OUT')
    V.key(m.transform, "scale_x", f(t0 + 8), 1.0, 'LINEAR'); V.key(m.transform, "scale_y", f(t0 + 8), 1.0, 'LINEAR')
    V.key(m.transform, "scale_x", f(t0 + 30), 1.035, 'LINEAR'); V.key(m.transform, "scale_y", f(t0 + 30), 1.035, 'LINEAR')
    wp = V.adjustment(ed, f"Whip {i + 1}", 6, f(t0 - 5), f(t0 + 6))
    X.attach(wp, X.whip(f"FX Whip {i + 1}", f(t0), direction=1 if i % 2 == 0 else -1))
for label, cinfo in man["counters"].items():
    st = cinfo["start"]
    n = len(cinfo["files"])
    cs = V.image_seq(ed, f"Counter {label}", cinfo["files"], 4, f(st), f(st + n), 540, 1540)
    V.key(cs.transform, "offset_x", f(st), V.ox(540) - 900, 'CUBIC', 'EASE_OUT')
    V.key(cs.transform, "offset_x", f(st + 10), V.ox(540), 'LINEAR')
    V.fade(cs, f(st + n - 7), f(st + n - 1), 1, 0)

# ---------- BOSS (3D, speed-ramp, iris, slam)
dip = V.color(ed, "Dip to black", (0, 0, 0), 8, f(648), f(661))
V.keys(dip, "blend_alpha", [(f(648), 0.0), (f(656), 1.0)], 'SINE', 'EASE_IN')
bs = ed.strips.new_scene("Boss 3D (Demon Lord)", boss, 1, f(660))
b0 = bs.frame_final_start
try:
    bs.retiming_keys.add(timeline_frame=b0 + SLOW_A)
    k2 = bs.retiming_keys.add(timeline_frame=b0 + SLOW_B)
    k2.timeline_frame = b0 + SLOW_TO
    bs.retiming_keys[len(bs.retiming_keys) - 1].timeline_frame = f(780)   # keep tail at ~1x, end at section end
    report["retiming"] = [k.timeline_frame for k in bs.retiming_keys]
except Exception as e:
    report["retiming_err"] = str(e)
report["boss_range"] = [bs.frame_final_start, bs.frame_final_end]
SLAM = 660 + SLOW_A + (SLAM_CONTENT - SLOW_A) * (SLOW_TO - SLOW_A) / (SLOW_B - SLOW_A)
report["slam_t"] = SLAM
bs.frame_final_end = f(780)
X.attach(bs, X.iris("FX Iris", f(660), f(676), aspect=C.W / C.H))

fl2 = V.color(ed, "Flash slam", (1, 1, 1), 8, f(SLAM), f(SLAM + 4))
V.keys(fl2, "blend_alpha", [(f(SLAM), 0.9), (f(SLAM + 3), 0.0)], 'LINEAR')
sh = V.adjustment(ed, "Slam punch+shake", 7, f(SLAM), f(SLAM + 34))
V.anim_scale(sh.transform, [(f(SLAM), 1.18), (f(SLAM + 10), 1.05), (f(SLAM + 34), 1.0)], 'EXPO', 'EASE_OUT')
V.shake(sh.transform, f(SLAM), f(SLAM + 34), strength=38, speed=1.2, seed=2)
X.attach(sh, X.ca_pulse("FX CA slam", [f(SLAM)], peak=0.12, decay=14))
tl = V.text(ed, "Title DEMON LORD", "DEMON LORD", 5, f(SLAM), f(778), 540, 1480, FT, 150, (1, 0.2, 0.12, 1),
            outline=((0.05, 0, 0, 1), 0.14))
tl.transform.origin = (0.5, 1 - 1480 / C.H)
V.anim_scale(tl.transform, [(f(SLAM), 2.6), (f(SLAM + 8), 1.0)], 'EXPO', 'EASE_OUT')
V.fade(tl, f(SLAM), f(SLAM + 3))
wv = V.text(ed, "Title WAVE 100", "WAVE 100", 4, f(SLAM + 8), f(778), 540, 1625, FT, 64, (0.08, 0.06, 0.15, 1),
            box=YEL4[:3] + (0.95,), box_margin=0.012, shadow=False)
V.key(wv, "location", f(SLAM + 8), (0.5, 1 - 1700 / C.H), 'BACK', 'EASE_OUT')
V.key(wv, "location", f(SLAM + 18), (0.5, 1 - 1625 / C.H), 'LINEAR')
V.fade(wv, f(SLAM + 8), f(SLAM + 12))
g2 = V.adjustment(ed, "Glitch boss->adapt", 6, f(773), f(787))
X.attach(g2, X.glitch("FX Glitch 2", f(773), f(787), seed=11))

# ---------- ADAPTIVE (meta: blurred fill + PiP card + phone), crossfade to outro
a_bg = V.image(ed, "Adapt BG", IMG["adapt_bg.png"], 1, f(780), f(945), 540, 960)
a_bl = ed.strips.new_effect("Adapt BG blur", 'GAUSSIAN_BLUR', channel=2, frame_start=f(780), length=f(945) - f(780), input1=a_bg)
a_bl.size_x = a_bl.size_y = 45
a_dim = V.color(ed, "Adapt dim", (0.02, 0.02, 0.06), 3, f(780), f(945), alpha=0.45)
card = V.image(ed, "PiP landscape card", IMG["card_landscape.png"], 4, f(788), f(945), 540, 600)
V.key(card.transform, "offset_x", f(788), V.ox(-620), 'CUBIC', 'EASE_OUT')
V.key(card.transform, "offset_x", f(804), V.ox(540), 'LINEAR')
ph = V.image(ed, "PiP phone", IMG["phone.png"], 5, f(800), f(945), 540, 1440)
V.key(ph.transform, "offset_y", f(800), V.oy(2500), 'BACK', 'EASE_OUT')
V.key(ph.transform, "offset_y", f(818), V.oy(1440), 'LINEAR')
t_web = V.text(ed, "Label WEB", "WEB  ·  16:9", 6, f(806), f(945), 540, 268, FB, 52, (1, 1, 1, 1), box=(0, 0, 0, 0.6), box_margin=0.012)
t_ph = V.text(ed, "Label PHONE", "PHONE\n9:16", 7, f(818), f(945), 870, 1440, FB, 52, YEL4, box=(0, 0, 0, 0.6), box_margin=0.012)
V.fade(t_web, f(806), f(814)); V.fade(t_ph, f(818), f(826))
adapt = V.meta(ed, "Adapt section", 1, [a_bg, a_bl, a_dim, card, ph, t_web, t_ph], f(945))
obg = V.image(ed, "Outro BG", IMG["outro_bg.png"], 2, f(915), f(1050), 540, 960, alpha_over=False)
cross = ed.strips.new_effect("Crossfade adapt->outro", 'CROSS', channel=3, frame_start=f(915), length=30, input1=adapt, input2=obg)

# ---------- OUTRO
lg = V.image(ed, "Logo", IMG["logo.png"], 4, f(932), f(1050), 540, 760)
V.anim_scale(lg.transform, [(f(932), 0.3), (f(946), 1.0)], 'BACK', 'EASE_OUT')
V.key(lg.transform, "scale_x", f(1050), 1.04, 'LINEAR'); V.key(lg.transform, "scale_y", f(1050), 1.04, 'LINEAR')
V.fade(lg, f(932), f(938))
sub = V.text(ed, "Outro subtitle", "VOXEL SURVIVOR  ·  SOLO DEV", 5, f(945), f(1050), 540, 905, FB, 46, (1, 1, 1, 0.92))
V.fade(sub, f(945), f(955))
bt = V.image(ed, "Button FOLLOW", IMG["btn_follow.png"], 3, f(955), f(1050), 540, 1440)
V.anim_scale(bt.transform, [(f(955), 0.4), (f(967), 1.0)], 'BACK', 'EASE_OUT')
for t in range(975, 1040, 15):      # pulse on the beat
    V.anim_scale(bt.transform, [(f(t), 1.07), (f(t + 8), 1.0)], 'QUAD', 'EASE_OUT')
V.fade(bt, f(955), f(959))
fb = V.color(ed, "Fade to black", (0, 0, 0), 8, f(1034), f(1050))
V.keys(fb, "blend_alpha", [(f(1034), 0.0), (f(1049), 1.0)], 'SINE', 'EASE_IN')

# ---------- CAPTIONS (karaoke, from TTS word timings)
caps = sorted(man["captions"], key=lambda c: c["start"])
for i, c in enumerate(caps):
    end = c["end"] if i + 1 >= len(caps) else min(c["end"], caps[i + 1]["start"])
    if end <= c["start"]:
        continue
    s_ = V.image(ed, f"Cap {os.path.basename(c['file'])[:-4]}", c["file"], 9, f(c["start"]), f(end), 540, c["y"])
    if c["first"]:
        s_.transform.origin = (0.5, 0.5)
        V.anim_scale(s_.transform, [(f(c["start"]), 0.82), (f(c["start"]) + 5, 1.0)], 'BACK', 'EASE_OUT')

# ---------- PROGRESS BAR
for name, rgb, a, ch in (("Progress track", (0, 0, 0), 0.4, 10), ("Progress bar", C.YELLOW, 1.0, 11)):
    pb = V.color(ed, name, rgb, ch, f(0), f(C.TOTAL), alpha=a)
    pb.transform.origin = (0.0, 1.0)
    pb.transform.scale_y = 12 / C.H
    if ch == 11:
        V.keys(pb.transform, "scale_x", [(f(0), 0.0), (f(C.TOTAL - 1), 1.0)], 'LINEAR')

# ---------- GRADE
gr = V.adjustment(ed, "Grade (bloom, CA, grain, vignette)", 12, f(0), f(C.TOTAL))
X.attach(gr, X.grade())

# ---------- AUDIO
for v in man["vo"]:
    V.sound(ed, f"VO {v['id']}", v["file"], 13, f(v["start"]))
mu = V.sound(ed, "Music (procedural 120 BPM)", AUD["music"], 14, f(0), 0.85)
mu.frame_final_end = f(C.TOTAL)
duck = [(f(0), 0.85)]
for v in man["vo"]:
    a, b = v["start"], v["start"] + v["frames"]
    duck += [(f(a) - 6, 0.85), (f(a), 0.33), (f(b), 0.33), (f(b) + 8, 0.85)]
duck += [(f(C.TOTAL - 20), 0.85), (f(C.TOTAL - 1), 0.0)]
last = -1
for fr, vol in duck:
    if fr > last:
        V.key(mu, "volume", fr, vol, 'LINEAR'); last = fr

sfx_events = [(15, "riser", 0.8), (120, "impact", 0.9), (126, "pop", 0.6), (292, "glitch", 0.7),
              (312, "whoosh", 0.5), (418, "whoosh", 0.5), (648, "whoosh_long", 0.45), (SLAM, "impact", 1.0),
              (SLAM + 8, "pop", 0.4), (772, "glitch", 0.7), (788, "whoosh", 0.5), (800, "whoosh", 0.5),
              (930, "impact", 0.45), (955, "pop", 0.6)]
sfx_events += [(t - 6, "whoosh", 0.55) for t in range(480, 660, 30)]
for st, _, _ in C.COUNTERS:
    sfx_events += [(st, "pop", 0.5), (st + 18, "ding", 0.35)]
ch_end = {15: 0, 16: 0, 17: 0}
for t, name, vol in sorted(sfx_events):
    ch = next((c for c, e in ch_end.items() if e <= f(t)), None)
    if ch is None:
        print("no free SFX channel at", t); continue
    s_ = V.sound(ed, f"SFX {name} @{int(t)}", AUD[name], ch, f(t), vol)
    ch_end[ch] = s_.frame_final_end

# ---------- render settings + save
edit.audio_volume = 0.6        # master headroom: VO + music + SFX summed clipped at 1.0 (final loudness is set by ffmpeg)
r = edit.render
r.image_settings.media_type = 'VIDEO'
r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format, r.ffmpeg.codec = 'MPEG4', 'H264'
r.ffmpeg.constant_rate_factor, r.ffmpeg.ffmpeg_preset = 'HIGH', 'GOOD'
r.ffmpeg.gopsize = C.FPS
r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_channels, r.ffmpeg.audio_mixrate = 'AAC', 192, 'STEREO', 48000
os.makedirs(C.OUT, exist_ok=True)
r.filepath = os.path.join(C.OUT, "projectb_devlog_raw.mp4")
r.use_file_extension = False
# Blender 5.x: the Video Editing workspace shows its own "sequencer scene" – point every workspace at Edit
for ws in bpy.data.workspaces:
    if hasattr(ws, "sequencer_scene"):
        ws.sequencer_scene = edit
for s_ in ed.strips_all:
    s_.select = False
edit.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=C.BLEND)
report["strips"] = len(ed.strips_all)
report["images_missing"] = [i.name for i in bpy.data.images if i.source == 'FILE' and not os.path.exists(bpy.path.abspath(i.filepath))]
print("REPORT>>" + json.dumps(report))
