"""Compositor node-group effects for VSE strips (Blender 5.x 'COMPOSITOR' strip modifier).
Each builder returns a node group; attach with `attach(strip, group)`. Groups are normal
datablocks: open them in the Compositor editor to tweak, keys live on node sockets."""
import random
import bpy
from .vse import key


def _inp(node, name, kind=None):
    for s in node.inputs:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(f"{node.bl_idname}: no input {name} ({kind})")


def _out(node, name):
    for s in node.outputs:
        if s.name == name and s.enabled:
            return s
    return node.outputs[name]


def new_group(name):
    ng = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='INPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    gi = ng.nodes.new('NodeGroupInput'); gi.location = (-900, 0)
    go = ng.nodes.new('NodeGroupOutput'); go.location = (900, 0)
    return ng, gi, go


def node(ng, t, x=0, y=0, **inputs):
    n = ng.nodes.new(t)
    n.location = (x, y)
    for k, v in inputs.items():
        _inp(n, k.replace('_', ' ')).default_value = v
    return n


def mix(ng, blend='MIX', x=0, y=0, factor=1.0):
    n = ng.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = blend
    n.location = (x, y)
    _inp(n, 'Factor', 'VALUE').default_value = factor
    return n


def mix_io(n):
    return _inp(n, 'Factor', 'VALUE'), _inp(n, 'A', 'RGBA'), _inp(n, 'B', 'RGBA'), [o for o in n.outputs if o.type == 'RGBA'][0]


def attach(strip, ng, name=None):
    m = strip.modifiers.new(name or ng.name, 'COMPOSITOR')
    m.node_group = ng
    return m


# ------------------------------------------------------------------ effects
def grade(name="FX Grade", lift=(0.97, 0.99, 1.04), gain=(1.06, 1.0, 0.93), saturation=1.12,
          bloom=0.45, bloom_threshold=0.85, dispersion=0.008, grain=0.07, vignette=0.45):
    """Colour grade + bloom + chromatic aberration + animated film grain + vignette."""
    ng, gi, go = new_group(name)
    L = ng.links
    cb = node(ng, 'CompositorNodeColorBalance', -650, 0)
    _inp(cb, 'Lift', 'RGBA').default_value = (*lift, 1)
    _inp(cb, 'Gain', 'RGBA').default_value = (*gain, 1)
    hs = node(ng, 'CompositorNodeHueSat', -450, 0, Saturation=saturation)
    gl = node(ng, 'CompositorNodeGlare', -250, 0)
    _inp(gl, 'Type').default_value = 'Bloom'
    _inp(gl, 'Threshold').default_value = bloom_threshold
    _inp(gl, 'Strength').default_value = bloom
    _inp(gl, 'Size').default_value = 0.6
    ld = node(ng, 'CompositorNodeLensdist', -50, 0, Dispersion=dispersion)
    _inp(ld, 'Fit').default_value = True
    L.new(gi.outputs[0], _inp(cb, 'Image')); L.new(cb.outputs[0], _inp(hs, 'Image'))
    L.new(hs.outputs[0], _inp(gl, 'Image')); L.new(_out(gl, 'Image'), _inp(ld, 'Image'))
    # grain: 4D noise animated by scene time
    tc = ng.nodes.new('CompositorNodeImageCoordinates'); tc.location = (-450, -350)
    st = ng.nodes.new('CompositorNodeSceneTime'); st.location = (-450, -550)
    mul = ng.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.location = (-250, -550)
    mul.inputs[1].default_value = 0.37
    L.new(_out(st, 'Frame'), mul.inputs[0])
    nz = ng.nodes.new('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'; nz.location = (-50, -350)
    pix = [o for o in tc.outputs if o.name.lower().startswith('pixel')]
    if pix:
        L.new(pix[0], _inp(nz, 'Vector')); _inp(nz, 'Scale').default_value = 0.55
    else:
        L.new(tc.outputs[0], _inp(nz, 'Vector')); _inp(nz, 'Scale').default_value = 700
    _inp(nz, 'Detail').default_value = 0.0
    L.new(mul.outputs[0], _inp(nz, 'W'))
    gm = mix(ng, 'OVERLAY', 200, 0, grain)
    f, a, b, o = mix_io(gm)
    L.new(ld.outputs[0], a); L.new(_out(nz, 'Factor'), b)
    # vignette
    em = node(ng, 'CompositorNodeEllipseMask', -50, -750)
    _inp(em, 'Size').default_value = (1.15, 0.85)
    bl = node(ng, 'CompositorNodeBlur', 150, -750)
    _inp(bl, 'Size').default_value = (260, 260)
    L.new(em.outputs[0], _inp(bl, 'Image'))
    inv = ng.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.location = (350, -750)
    inv.inputs[0].default_value = 1.0
    L.new(bl.outputs[0], inv.inputs[1])
    amt = ng.nodes.new('ShaderNodeMath'); amt.operation = 'MULTIPLY'; amt.location = (500, -750)
    amt.inputs[1].default_value = vignette
    L.new(inv.outputs[0], amt.inputs[0])
    vm = mix(ng, 'MIX', 600, 0)
    vf, va, vb, vo = mix_io(vm)
    vb.default_value = (0, 0, 0, 1)
    L.new(o, va); L.new(amt.outputs[0], vf)
    L.new(vo, go.inputs[0])
    return ng


def whip(name, cut, direction=1, half=5, width=1080, blur=0.22, dispersion=0.07):
    """Whip-pan transition centred on frame `cut` (use on an adjustment strip spanning cut±half)."""
    ng, gi, go = new_group(name)
    L = ng.links
    tr = node(ng, 'CompositorNodeTranslate', -500, 0)
    _inp(tr, 'Extension X').default_value = 'Repeat'
    _inp(tr, 'Extension Y').default_value = 'Repeat'
    db = node(ng, 'CompositorNodeDBlur', -200, 0, Samples=24)
    ld = node(ng, 'CompositorNodeLensdist', 100, 0)
    _inp(ld, 'Fit').default_value = True
    L.new(gi.outputs[0], _inp(tr, 'Image')); L.new(tr.outputs[0], _inp(db, 'Image'))
    L.new(db.outputs[0], _inp(ld, 'Image')); L.new(ld.outputs[0], go.inputs[0])
    d = direction * width * 0.55
    sx = _inp(tr, 'X')
    key(sx, 'default_value', cut - half, 0.0, 'QUAD', 'EASE_IN')
    key(sx, 'default_value', cut - 1, -d, 'CONSTANT')
    key(sx, 'default_value', cut, d, 'QUAD', 'EASE_OUT')
    key(sx, 'default_value', cut + half, 0.0, 'LINEAR')
    am = _inp(db, 'Amount')
    for fr, v in ((cut - half, 0.0), (cut - 1, blur), (cut, blur), (cut + half, 0.0)):
        key(am, 'default_value', fr, v, 'SINE', 'EASE_IN_OUT')
    dp = _inp(ld, 'Dispersion')
    for fr, v in ((cut - half, 0.0), (cut, dispersion), (cut + half, 0.0)):
        key(dp, 'default_value', fr, v, 'SINE', 'EASE_IN_OUT')
    return ng


def glitch(name, start, end, seed=1, max_split=38, max_jitter=90):
    """Digital glitch: RGB split + horizontal jitter + pixelation bursts, randomised per frame."""
    rnd = random.Random(seed)
    ng, gi, go = new_group(name)
    L = ng.links
    sep = ng.nodes.new('CompositorNodeSeparateColor'); sep.location = (-650, 0)
    com = ng.nodes.new('CompositorNodeCombineColor'); com.location = (-150, 0)
    tr_r = node(ng, 'CompositorNodeTranslate', -400, 150)
    tr_b = node(ng, 'CompositorNodeTranslate', -400, -150)
    jit = node(ng, 'CompositorNodeTranslate', 50, 0)
    _inp(jit, 'Extension X').default_value = 'Repeat'
    px = ng.nodes.new('CompositorNodePixelate'); px.location = (300, 0)
    L.new(gi.outputs[0], sep.inputs[0])
    L.new(_out(sep, 'Red'), _inp(tr_r, 'Image')); L.new(tr_r.outputs[0], _inp(com, 'Red'))
    L.new(_out(sep, 'Green'), _inp(com, 'Green'))
    L.new(_out(sep, 'Blue'), _inp(tr_b, 'Image')); L.new(tr_b.outputs[0], _inp(com, 'Blue'))
    L.new(_out(sep, 'Alpha'), _inp(com, 'Alpha'))
    L.new(com.outputs[0], _inp(jit, 'Image')); L.new(jit.outputs[0], _inp(px, 'Color'))
    L.new(px.outputs[0], go.inputs[0])
    n = end - start
    for i, fr in enumerate(range(start, end + 1)):
        env = 1 - abs((i - n / 2) / (n / 2 + 1e-6))
        on = fr < end and rnd.random() < 0.85
        split = rnd.uniform(0.3, 1.0) * max_split * env if on else 0.0
        key(_inp(tr_r, 'X'), 'default_value', fr, split, 'CONSTANT')
        key(_inp(tr_b, 'X'), 'default_value', fr, -split, 'CONSTANT')
        key(_inp(tr_r, 'Y'), 'default_value', fr, rnd.uniform(-6, 6) * env if on else 0.0, 'CONSTANT')
        j = rnd.uniform(-1, 1) * max_jitter * env if (on and rnd.random() < 0.5) else 0.0
        key(_inp(jit, 'X'), 'default_value', fr, j, 'CONSTANT')
        size = rnd.choice([10, 16, 24]) if (on and rnd.random() < 0.25) else 1
        key(_inp(px, 'Size'), 'default_value', fr, size, 'CONSTANT')
    return ng


def iris(name, start, end, aspect=1080 / 1920, soft=60, max_size=2.4):
    """Circular iris reveal from black (circle in pixels thanks to `aspect` correction)."""
    ng, gi, go = new_group(name)
    L = ng.links
    em = node(ng, 'CompositorNodeEllipseMask', -500, -250)
    bl = node(ng, 'CompositorNodeBlur', -250, -250)
    _inp(bl, 'Size').default_value = (soft, soft)
    L.new(em.outputs[0], _inp(bl, 'Image'))
    m = mix(ng, 'MIX', 0, 0)
    f, a, b, o = mix_io(m)
    a.default_value = (0, 0, 0, 1)
    L.new(gi.outputs[0], b); L.new(bl.outputs[0], f); L.new(o, go.inputs[0])
    sz = _inp(em, 'Size')
    key(sz, 'default_value', start, (0.001, 0.001 / aspect), 'EXPO', 'EASE_IN')
    key(sz, 'default_value', end, (max_size, max_size / aspect), 'LINEAR')
    return ng


def ca_pulse(name, frames, peak=0.09, decay=8):
    """Chromatic-aberration hits on given frames."""
    ng, gi, go = new_group(name)
    ld = node(ng, 'CompositorNodeLensdist', 0, 0)
    _inp(ld, 'Fit').default_value = True
    ng.links.new(gi.outputs[0], _inp(ld, 'Image')); ng.links.new(ld.outputs[0], go.inputs[0])
    dp = _inp(ld, 'Dispersion')
    key(dp, 'default_value', max(1, frames[0] - 1), 0.0, 'LINEAR')
    for fr in frames:
        key(dp, 'default_value', fr, peak, 'EXPO', 'EASE_OUT')
        key(dp, 'default_value', fr + decay, 0.0, 'LINEAR')
    return ng
