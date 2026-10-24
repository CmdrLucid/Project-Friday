#!/usr/bin/env python3
"""GLB (kiln output) -> .r3m (the remake's simple model file): 'R3M1', u32 triangle count, per triangle 9 float32 (three xyz, glTF coordinates: metres, Y up, +Z front),
3 bytes colour (base colour factor as sRGB) and a flags byte (bit 0 = emissive).  Node transforms (translation / rotation / scale / matrix) are applied.  No dependencies.
usage: glb2r3m.py in.glb out.r3m"""
import sys, json, struct, math
def read_glb(path):
    d = open(path, "rb").read()
    magic, ver, ln = struct.unpack_from("<III", d, 0); assert magic == 0x46546C67, "not a GLB"
    off = 12; js = None; bn = b""
    while off < ln:
        cl, ct = struct.unpack_from("<II", d, off); chunk = d[off + 8: off + 8 + cl]; off += 8 + cl
        if ct == 0x4E4F534A: js = json.loads(chunk)
        elif ct == 0x004E4942: bn = chunk
    return js, bn
def accessor(js, bn, idx):
    a = js["accessors"][idx]; bv = js["bufferViews"][a["bufferView"]]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B", 5122: "h", 5120: "b"}[a["componentType"]]
    size = struct.calcsize("<" + fmt); stride = bv.get("byteStride") or size * ncomp
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0); out = []
    for i in range(a["count"]):
        out.append(struct.unpack_from("<" + fmt * ncomp, bn, base + i * stride))
    return out
def mat_mul(a, b):  # 4x4 column-major
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]
def node_matrix(n):
    if "matrix" in n: return list(n["matrix"])
    t = n.get("translation", [0, 0, 0]); q = n.get("rotation", [0, 0, 0, 1]); s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    r = [1 - 2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w), 0,  2*(x*y-z*w), 1 - 2*(x*x+z*z), 2*(y*z+x*w), 0,  2*(x*z+y*w), 2*(y*z-x*w), 1 - 2*(x*x+y*y), 0,  0, 0, 0, 1]
    m = [r[0]*s[0], r[1]*s[0], r[2]*s[0], 0,  r[4]*s[1], r[5]*s[1], r[6]*s[1], 0,  r[8]*s[2], r[9]*s[2], r[10]*s[2], 0,  t[0], t[1], t[2], 1]
    return m
def xf(m, p): return (m[0]*p[0] + m[4]*p[1] + m[8]*p[2] + m[12], m[1]*p[0] + m[5]*p[1] + m[9]*p[2] + m[13], m[2]*p[0] + m[6]*p[1] + m[10]*p[2] + m[14])
def srgb(c): c = max(0.0, min(1.0, c)); return int(round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)))
def main(src, dst):
    js, bn = read_glb(src); tris = []
    def walk(ni, parent):
        n = js["nodes"][ni]; m = mat_mul(parent, node_matrix(n))
        if "mesh" in n:
            for pr in js["meshes"][n["mesh"]]["primitives"]:
                pos = accessor(js, bn, pr["attributes"]["POSITION"]); idx = [i[0] for i in accessor(js, bn, pr["indices"])] if "indices" in pr else list(range(len(pos)))
                mt = js["materials"][pr["material"]] if "material" in pr else {}
                bc = mt.get("pbrMetallicRoughness", {}).get("baseColorFactor", [0.8, 0.8, 0.8, 1]); em = mt.get("emissiveFactor", [0, 0, 0])
                col = (srgb(bc[0]), srgb(bc[1]), srgb(bc[2])); flags = 1 if max(em) > 0.05 else 0
                for k in range(0, len(idx) - 2, 3):
                    tris.append(([xf(m, pos[idx[k + j]]) for j in range(3)], col, flags))
        for c in n.get("children", []): walk(c, m)
    ident = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    sc = js["scenes"][js.get("scene", 0)]
    for ni in sc["nodes"]: walk(ni, ident)
    with open(dst, "wb") as f:
        f.write(b"R3M1"); f.write(struct.pack("<I", len(tris)))
        for p, col, fl in tris:
            f.write(struct.pack("<9f", *[v for q in p for v in q])); f.write(bytes([col[0], col[1], col[2], fl]))
    print("%s: %d triangles" % (dst, len(tris)))
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
