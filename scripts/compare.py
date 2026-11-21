"""Compare ember screenshots with reference images, standard library only.

  compare.py png <in.bmp> <out.png>                  convert an ember BMP to PNG
  compare.py check <shots dir> <reference dir> <out dir> [--max-bad PCT] [--max-mean V]

ember writes 32-bit top-down BMPs. A pixel is "bad" when any channel differs by more than
16 of 255; different GPUs rasterise and round slightly differently, so a few bad pixels at
edges are normal, while a missing shadow or object shows up as a large bad fraction.
"""
import json, os, struct, sys, zlib


def read_bmp(path):
    d = open(path, "rb").read()
    off, w, h = struct.unpack_from("<I", d, 10)[0], *struct.unpack_from("<ii", d, 18)
    assert h < 0, "expected a top-down BMP"
    h = -h
    px = d[off:off + w * h * 4]
    rgb = bytearray(w * h * 3)
    rgb[0::3], rgb[1::3], rgb[2::3] = px[2::4], px[1::4], px[0::4]
    return w, h, bytes(rgb)


def write_png(path, w, h, rgb):
    raw = b"".join(b"\0" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    chunk = lambda t, b: struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def read_png(path):
    """Reads the PNGs write_png makes (8-bit RGB, filter 0 on every row)."""
    d = open(path, "rb").read()
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(d):
        n, t = struct.unpack_from(">I4s", d, pos)
        body = d[pos + 8:pos + 8 + n]
        if t == b"IHDR":
            w, h = struct.unpack_from(">II", body)
        elif t == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    assert all(raw[y * stride] == 0 for y in range(h)), "unsupported PNG filter"
    return w, h, b"".join(raw[y * stride + 1:(y + 1) * stride] for y in range(h))


def check(shots, refs, out, max_bad, max_mean):
    os.makedirs(out, exist_ok=True)
    rows, ok = [], True
    for name in sorted(f[:-4] for f in os.listdir(shots) if f.endswith(".bmp")):
        w, h, a = read_bmp(os.path.join(shots, name + ".bmp"))
        write_png(os.path.join(out, name + ".png"), w, h, a)
        ref = os.path.join(refs, name + ".png")
        if not os.path.exists(ref):
            rows.append({"scene": name, "status": "FAIL: no reference"})
            ok = False
            continue
        rw, rh, b = read_png(ref)
        if (rw, rh) != (w, h):
            rows.append({"scene": name, "status": f"size {w}x{h} vs {rw}x{rh}"})
            ok = False
            continue
        diff = bytes(abs(x - y) for x, y in zip(a, b))
        per_px = [max(diff[i:i + 3]) for i in range(0, len(diff), 3)]
        bad = sum(1 for v in per_px if v > 16) / len(per_px) * 100
        mean = sum(diff) / len(diff)
        # Heat map: bad pixels red, small differences grey, the rest black.
        heat = bytearray(len(a))
        for i, v in enumerate(per_px):
            heat[i * 3:i * 3 + 3] = (255, 40, 40) if v > 16 else (v * 8,) * 3
        write_png(os.path.join(out, name + ".diff.png"), w, h, bytes(heat))
        passed = bad <= max_bad and mean <= max_mean
        ok &= passed
        rows.append({"scene": name, "status": "pass" if passed else "FAIL", "bad_pct": round(bad, 3), "mean": round(mean, 3)})
    # A reference with no screenshot means that scene didn't render.
    shot = {r["scene"] for r in rows}
    for name in sorted(f[:-4] for f in os.listdir(refs) if f.endswith(".png") and f[:-4] not in shot):
        rows.append({"scene": name, "status": "FAIL: not rendered"})
        ok = False
    table = "| scene | result | bad pixels % | mean diff |\n|---|---|---|---|\n" + "".join(
        f"| {r['scene']} | {r['status']} | {r.get('bad_pct', '')} | {r.get('mean', '')} |\n" for r in rows)
    print(table)
    json.dump(rows, open(os.path.join(out, "results.json"), "w"), indent=1)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a").write(f"### Screenshots vs reference (bad > {max_bad}% or mean > {max_mean} fails)\n\n{table}\n")
    return ok


if __name__ == "__main__":
    if sys.argv[1] == "png":
        write_png(sys.argv[3], *read_bmp(sys.argv[2]))
    elif sys.argv[1] == "check":
        args = sys.argv[2:]
        get = lambda k, d: float(args[args.index(k) + 1]) if k in args else d
        sys.exit(0 if check(args[0], args[1], args[2], get("--max-bad", 2.0), get("--max-mean", 3.0)) else 1)
