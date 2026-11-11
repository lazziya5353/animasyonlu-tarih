"""13. Kat — Part 1 (20 sn) için 3D sahne: koridor → oda/telefon → banyo kapısı → asansör (13).
Blender (bpy) ile prosedürel kurulur, Cycles CPU ile render edilir. Yapay zekâ görseli kullanılmaz.
Kullanım: python engine/blender/otel13.py --out /tmp/otel13 [--w 720 --h 1280 --fps 24 --samples 24 --kare 1-480]
"""
import bpy, math, sys, argparse, os
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/tmp/otel13"); ap.add_argument("--w", type=int, default=720); ap.add_argument("--h", type=int, default=1280)
ap.add_argument("--fps", type=int, default=24); ap.add_argument("--samples", type=int, default=24); ap.add_argument("--kare", default="")
ap.add_argument("--blend", default="")
a = ap.parse_args([x for x in sys.argv[1:] if x != "--"] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])

FPS = a.fps; T = lambda s: int(round(s * FPS)) + 1
SAHNE = [("koridor", 0, 5.0), ("oda", 5.0, 9.6), ("banyo", 9.6, 14.4), ("asansor", 14.4, 20.0)]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = a.samples; sc.cycles.use_denoising = True
try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception: pass
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 2
sc.render.resolution_x, sc.render.resolution_y = a.w, a.h; sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, T(20.0) - 1
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy" if "AgX - Punchy" in [l.name for l in []] else "None"
sc.view_settings.exposure = float(os.environ.get("POZ", "0.3"))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.003, 0.003, 0.005, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1
# hafif sis (hacim): ışık huzmeleri görünsün
sc.render.film_transparent = False


def mat(ad, renk, rough=0.6, emis=None, guc=0.0, metal=0.0):
    m = bpy.data.materials.new(ad); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*renk, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emis:
        b.inputs["Emission Color"].default_value = (*emis, 1); b.inputs["Emission Strength"].default_value = guc
    return m


def kutu(ad, loc, boyut, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot); o = bpy.context.object; o.name = ad
    o.scale = (boyut[0] / 2, boyut[1] / 2, boyut[2] / 2); o.data.materials.append(m); return o


def yazi(ad, metin, loc, boyut, m, rot=(math.radians(90), 0, 0)):
    bpy.ops.object.text_add(location=loc, rotation=rot); o = bpy.context.object; o.name = ad
    o.data.body = metin; o.data.size = boyut; o.data.align_x = "CENTER"; o.data.align_y = "CENTER"; o.data.extrude = 0.005
    o.data.materials.append(m); return o


def isik(ad, tip, loc, enerji, renk=(1, .85, .6), boyut=0.3, rot=(0, 0, 0)):
    d = bpy.data.lights.new(ad, tip); d.energy = enerji; d.color = renk
    if tip == "AREA": d.size = boyut
    elif tip in ("POINT", "SPOT"): d.shadow_soft_size = boyut
    o = bpy.data.objects.new(ad, d); o.location = loc; o.rotation_euler = rot; sc.collection.objects.link(o)
    o.visible_camera = False; o.visible_glossy = False
    return o


def kf(obj, yol, deger, t, idx=None):
    setattr(obj, yol, deger) if idx is None else getattr(obj, yol).__setitem__(idx, deger)
    obj.keyframe_insert(data_path=yol, frame=t, index=-1 if idx is None else idx)


# ── malzemeler ──
DUVAR = mat("duvar", (0.09, 0.025, 0.025), 0.8)          # koyu bordo duvar kâğıdı
SUPURGE = mat("supurge", (0.08, 0.05, 0.03), 0.5)
HALI = mat("hali", (0.05, 0.012, 0.015), 0.95)
TAVAN = mat("tavan", (0.08, 0.07, 0.065), 0.9)
KAPI = mat("kapi", (0.12, 0.07, 0.04), 0.45)
PIRINC = mat("pirinc", (0.7, 0.5, 0.2), 0.3, metal=1.0)
LAMBA = mat("lamba", (1, .9, .7), 0.5, emis=(1, .8, .5), guc=12)
KIRMIZI = mat("kirmizi_led", (0.1, 0, 0), 0.4, emis=(1, 0.05, 0.02), guc=30)
CARSAF = mat("carsaf", (0.6, 0.58, 0.55), 0.9)
AHSAP = mat("ahsap", (0.15, 0.09, 0.05), 0.55)
SIYAH = mat("siyah", (0.01, 0.01, 0.01), 0.3)
CELIK = mat("celik", (0.5, 0.5, 0.52), 0.25, metal=1.0)
SILUET = mat("siluet", (0.0, 0.0, 0.0), 1.0)
CINI = mat("cini", (0.55, 0.6, 0.6), 0.2)

# ═══ 1) KORİDOR (x=0 hattı, y boyunca uzanır) ═══
L = 22
kutu("k_zemin", (0, L / 2, 0), (2.4, L, 0.05), HALI)
kutu("k_tavan", (0, L / 2, 2.8), (2.4, L, 0.05), TAVAN)
kutu("k_sol", (-1.2, L / 2, 1.4), (0.05, L, 2.8), DUVAR); kutu("k_sag", (1.2, L / 2, 1.4), (0.05, L, 2.8), DUVAR)
kutu("k_son", (0, L, 1.4), (2.4, 0.05, 2.8), DUVAR)
for yan in (-1, 1):
    kutu(f"k_sup{yan}", (yan * 1.17, L / 2, 0.06), (0.02, L, 0.12), SUPURGE)
kapi_no = [1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308]
koridor_lamba = []
for i in range(8):
    y = 2.5 + i * 2.6; yan = -1 if i % 2 == 0 else 1
    kutu(f"kapi{i}", (yan * 1.165, y, 1.05), (0.04, 0.95, 2.1), KAPI)
    kutu(f"kol{i}", (yan * 1.13, y + 0.35, 1.0), (0.04, 0.12, 0.03), PIRINC)
    yazi(f"no{i}", str(kapi_no[i]), (yan * 1.14, y, 1.75), 0.12, PIRINC, rot=(math.radians(90), 0, math.radians(-90 * yan)))
    # tavan lambaları
    kutu(f"lamba{i}", (0, y, 2.76), (0.35, 0.35, 0.04), LAMBA)
    koridor_lamba.append(isik(f"kl{i}", "AREA", (0, y, 2.7), 0 if i in (4, 6) else 25, (1, .72, .45), 0.4, rot=(0, 0, 0)))
# titreyen lamba (3. lamba): enerji anahtar kareleri
tit = koridor_lamba[2]
for k, (t, e) in enumerate([(0, 25), (1.2, 25), (1.25, 2), (1.32, 25), (1.36, 1), (1.5, 25), (2.8, 25), (2.84, 0), (3.1, 0), (3.15, 25), (4.2, 25), (4.25, 1), (4.4, 25)]):
    tit.data.energy = e; tit.data.keyframe_insert("energy", frame=T(t))
lamba_mesh = bpy.data.objects["lamba2"]
# koridorun sonu: kırmızı "ACİL ÇIKIŞ" ışığı ve karanlık
yazi("cikis", "ÇIKIŞ", (0, L - 0.05, 2.35), 0.16, KIRMIZI, rot=(math.radians(90), 0, math.radians(180)))
isik("cikis_isik", "POINT", (0, L - 0.4, 2.3), 15, (1, .1, .05), 0.2)

# ═══ 2) ODA (x=30 civarı) ═══
OX = 30
kutu("o_zemin", (OX, 0, 0), (5, 5, 0.05), AHSAP); kutu("o_duvar1", (OX, 2.5, 1.4), (5, 0.05, 2.8), DUVAR)
kutu("o_duvar2", (OX - 2.5, 0, 1.4), (0.05, 5, 2.8), DUVAR); kutu("o_duvar3", (OX + 2.5, 0, 1.4), (0.05, 5, 2.8), DUVAR)
kutu("o_tavan", (OX, 0, 2.8), (5, 5, 0.05), TAVAN)
kutu("yatak", (OX - 0.6, 1.2, 0.3), (1.8, 2.2, 0.5), CARSAF); kutu("yastik", (OX - 0.6, 2.1, 0.62), (1.3, 0.35, 0.18), CARSAF)
kutu("basucu", (OX + 0.75, 1.9, 0.3), (0.55, 0.5, 0.6), AHSAP)
# eski telefon: gövde + ahize
tel = kutu("telefon", (OX + 0.75, 1.85, 0.66), (0.26, 0.2, 0.1), SIYAH)
ahize = kutu("ahize", (OX + 0.75, 1.85, 0.75), (0.3, 0.07, 0.06), SIYAH)
saat = kutu("saat", (OX + 0.92, 1.75, 0.67), (0.2, 0.08, 0.1), SIYAH, rot=(0, 0, math.radians(35)))
yazi("saat_led", "03:00", (OX + 0.96, 1.70, 0.675), 0.055, KIRMIZI, rot=(math.radians(90), 0, math.radians(35)))
isik("saat_isik", "POINT", (OX + 0.75, 1.9, 0.75), 0.6, (1, .05, .02), 0.05)
abajur = isik("abajur", "POINT", (OX + 0.75, 2.1, 1.05), 8, (1, .7, .4), 0.15)
ay = isik("ay", "AREA", (OX - 2.3, 0, 1.6), 25, (.5, .6, 1), 1.5, rot=(0, math.radians(90), 0))
# zil: telefon titreşimi + abajur nabzı (5.6 → 9.6 sn)
for f in range(T(5.6), T(9.5), 2):
    ahize.location.z = 0.75 + (0.012 if (f // 2) % 2 else 0); ahize.keyframe_insert("location", frame=f, index=2)
    ahize.rotation_euler.z = (0.04 if (f // 2) % 2 else -0.04); ahize.keyframe_insert("rotation_euler", frame=f, index=2)

# ═══ 3) BANYO KAPISI (x=60) ═══
BX = 60
kutu("b_zemin", (BX, 0, 0), (4, 8, 0.05), AHSAP)
for nm, cx, wd in (("b_duvar_s", BX - 1.25, 1.5), ("b_duvar_d", BX + 1.25, 1.5)): kutu(nm, (cx, 1.5, 1.4), (wd, 0.05, 2.8), DUVAR)
kutu("b_duvar_u", (BX, 1.5, 2.45), (1.0, 0.05, 0.7), DUVAR)
kutu("b_tavan", (BX, 0, 2.8), (4, 4, 0.05), TAVAN)
bkapi = kutu("b_kapi", (BX - 0.08, 1.47, 1.05), (0.8, 0.04, 2.1), KAPI)
kutu("b_aralik_isik", (BX + 0.38, 1.5, 1.05), (0.06, 0.01, 2.08), mat("aralik", (1, 1, 1), 0.5, emis=(.7, .85, 1), guc=18))
bkapi.data.vertices  # kapı hafif aralık: menteşe etrafında döndürmek için orijini sola al
bpy.context.view_layer.objects.active = bkapi
kutu("b_kasa_sol", (BX - 0.48, 1.47, 1.05), (0.06, 0.08, 2.2), AHSAP); kutu("b_kasa_sag", (BX + 0.48, 1.47, 1.05), (0.06, 0.08, 2.2), AHSAP)
kutu("b_ic", (BX, 3.6, 1.4), (2, 0.05, 2.8), CINI)
banyo_isik = isik("banyo_isik", "POINT", (BX, 2.3, 1.2), 40, (.75, .9, 1), 0.3)
cizgi = kutu("kapi_alti", (BX, 1.45, 0.01), (0.86, 0.02, 0.01), mat("kapi_alti_m", (1, 1, 1), 0.5, emis=(.7, .85, 1), guc=25))
kutu("b_kol", (BX + 0.35, 1.44, 1.0), (0.12, 0.04, 0.03), PIRINC)
# kapının altından gelen ışık titrer (biri içeride geziniyor gibi)
for t, e in [(9.6, 40), (11.0, 40), (11.15, 6), (11.4, 6), (11.55, 40), (13.0, 40), (13.1, 4), (13.5, 4), (13.6, 40)]:
    banyo_isik.data.energy = e; banyo_isik.data.keyframe_insert("energy", frame=T(t))
isik("b_ortam", "POINT", (BX - 1.2, -1, 2.2), 3, (1, .7, .45), 0.4)

# ═══ 4) ASANSÖR (x=90) ═══
AX = 90
kutu("a_zemin", (AX, 0, 0), (4, 8, 0.05), HALI)
for nm, cx in (("a_duvar_s", AX - 1.4), ("a_duvar_d", AX + 1.4)): kutu(nm, (cx, 1.0, 1.6), (1.3, 0.1, 3.2), DUVAR)
kutu("a_duvar_u", (AX, 1.0, 2.9), (1.5, 0.1, 0.6), DUVAR)
for nm, cx in (("a_kasa_s", AX - 0.72), ("a_kasa_d", AX + 0.72)): kutu(nm, (cx, 0.94, 1.15), (0.08, 0.06, 2.35), CELIK)
sol = kutu("a_kapi_sol", (AX - 0.33, 0.9, 1.1), (0.66, 0.04, 2.2), CELIK); sag = kutu("a_kapi_sag", (AX + 0.33, 0.9, 1.1), (0.66, 0.04, 2.2), CELIK)
KABIN = mat("kabin", (0.06, 0.06, 0.065), 0.35, metal=0.6)
kutu("a_arka", (AX, 3.2, 1.3), (1.5, 0.05, 2.6), KABIN); kutu("a_yan1", (AX - 0.75, 2.1, 1.3), (0.05, 2.2, 2.6), KABIN); kutu("a_yan2", (AX + 0.75, 2.1, 1.3), (0.05, 2.2, 2.6), KABIN); kutu("a_ktavan", (AX, 2.1, 2.6), (1.5, 2.2, 0.05), KABIN)
isik("a_arka_isik", "AREA", (AX, 3.1, 1.3), 18, (.6, .75, 1), 1.0, rot=(math.radians(90), 0, 0))
yazi("kat13", "13", (AX, 0.88, 2.55), 0.22, KIRMIZI)
isik("kat_isik", "POINT", (AX, 0.6, 2.5), 3, (1, .05, .02), 0.1)
kabin_isik = isik("kabin_isik", "AREA", (AX, 2.0, 2.45), 0, (.6, .8, 1), 0.8, rot=(0, 0, 0))
# siluet: kabinin içinde duran biri
# siluet: uzun paltolu, başı hafif eğik bir figür (kabinin dibinde, sırtı ışığa dönük)
def parca(tur, loc, olcek, rot=(0, 0, 0)):
    (bpy.ops.mesh.primitive_uv_sphere_add if tur == "k" else bpy.ops.mesh.primitive_cylinder_add)(location=loc, rotation=rot)
    o = bpy.context.object; o.scale = olcek; o.data.materials.append(SILUET); bpy.ops.object.shade_smooth(); return o
parca("s", (AX, 2.6, 0.7), (0.21, 0.13, 0.7))            # palto/gövde
parca("k", (AX, 2.6, 1.42), (0.24, 0.14, 0.12))           # omuzlar
parca("s", (AX, 2.6, 1.5), (0.06, 0.06, 0.08))            # boyun
parca("k", (AX + 0.02, 2.58, 1.66), (0.1, 0.11, 0.125), rot=(math.radians(12), 0, 0))  # baş, hafif öne eğik
for yan in (-1, 1): parca("s", (AX + yan * 0.24, 2.6, 1.05), (0.055, 0.055, 0.38), rot=(0, math.radians(yan * 4), 0))  # kollar
isik("a_tavan", "POINT", (AX, -1.5, 2.6), 15, (1, .75, .5), 0.4)
for t, x in [(14.4, 0.33), (15.6, 0.33), (17.2, 1.0)]:
    sol.location.x = AX - x; sol.keyframe_insert("location", frame=T(t), index=0); sag.location.x = AX + x; sag.keyframe_insert("location", frame=T(t), index=0)
for t, e in [(14.4, 0), (15.6, 0), (15.7, 30), (16.4, 30), (16.45, 2), (16.6, 30), (17.8, 30), (17.85, 0), (18.3, 0), (18.35, 30), (20, 30)]:
    kabin_isik.data.energy = e; kabin_isik.data.keyframe_insert("energy", frame=T(t))

# ═══ KAMERA: her sahnede ayrı yol, sahne geçişleri sert kesme ═══
cam_d = bpy.data.cameras.new("kam"); cam_d.lens = 24; cam = bpy.data.objects.new("kam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.8


def bak(src, hedef):
    d = Vector(hedef) - Vector(src); return d.to_track_quat("-Z", "Y").to_euler()


YOL = {  # (başlangıç konumu, bitiş konumu, bakış noktası, odak mesafesi, lens)
    "koridor": ((0, -0.5, 1.6), (0, 4.5, 1.55), (0, 20, 1.4), 6.0, 22),
    "oda": ((OX + 1.9, 0.2, 1.25), (OX + 1.45, 0.95, 0.95), (OX + 0.72, 1.95, 0.68), 1.2, 32),
    "banyo": ((BX - 0.6, -1.8, 1.5), (BX - 0.2, -0.3, 1.25), (BX, 1.47, 0.9), 2.0, 28),
    "asansor": ((AX + 0.3, -2.2, 1.55), (AX, -0.6, 1.45), (AX, 1.5, 1.4), 2.5, 26),
}
for ad, t0, t1 in SAHNE:
    p0, p1, h, odak, lens = YOL[ad]; f0, f1 = T(t0), T(t1) - 1
    for f, p in ((f0, p0), (f1, p1)):
        cam.location = p; cam.rotation_euler = bak(p, h); cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
        cam_d.lens = lens; cam_d.keyframe_insert("lens", frame=f); cam_d.dof.focus_distance = odak; cam_d.dof.keyframe_insert("focus_distance", frame=f)
# sahne içinde yumuşak, sahneler arasında sert geçiş
def egriler(ob):
    act = ob.animation_data.action
    if hasattr(act, "fcurves"): return list(act.fcurves)
    out = []
    for ly in act.layers:
        for st in ly.strips:
            for cb in st.channelbags: out += list(cb.fcurves)
    return out
for fc in egriler(cam):
    for k in fc.keyframe_points: k.interpolation = "BEZIER"
# kamera hafif el titremesi (gürültü)
for fc in egriler(cam):
    if fc.data_path == "rotation_euler":
        n = fc.modifiers.new("NOISE"); n.strength = 0.006; n.scale = 40

if a.blend: bpy.ops.wm.save_as_mainfile(filepath=a.blend)
os.makedirs(a.out, exist_ok=True)
kareler = range(sc.frame_start, sc.frame_end + 1)
if a.kare:
    if "-" in a.kare: x, y = map(int, a.kare.split("-")); kareler = range(x, y + 1)
    else: kareler = [int(v) for v in a.kare.split(",")]
for f in kareler:
    sc.frame_set(f); sc.render.filepath = os.path.join(a.out, f"{f:04d}.png"); bpy.ops.render.render(write_still=True)
    print("kare", f, flush=True)
