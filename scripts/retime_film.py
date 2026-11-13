"""Re-time hyperframes_film so each act lasts as long as its narration (no dead air), then patch index.html.

    .venv/Scripts/python.exe scripts/retime_film.py            # writes schedule.json and patches index.html
    cd hyperframes_film && npx --yes hyperframes@0.8.222 render -o renders/film_retimed.mp4

Act VI (live demo) keeps its 210 s: the recording and its on-screen scenario marks are fixed.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_voiceover import OUT, ROOT, parse_segments  # noqa: E402

LEAD, GAP, TAIL, LAST_TAIL, TEMPO = 2.5, 0.8, 2.5, 4.0, 0.95
ACT_SEGS = {1: (1, 4), 2: (5, 8), 3: (9, 12), 4: (13, 16), 5: (17, 20), 7: (28, 31)}
DEMO_SEGS = range(21, 28)
DEMO_LEN = 210.0


def natural(n: int) -> Path:
    """Segment n at a fixed natural tempo, internal long pauses trimmed."""
    dst = OUT / f"nat_{n:02d}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / f"seg_{n:02d}.wav"), "-af",
                    f"silenceremove=stop_periods=-1:stop_duration=0.9:stop_threshold=-45dB,atempo={TEMPO}", str(dst)], check=True)
    return dst


def dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout)


def build() -> dict:
    t, acts, seg_start = 0.0, {}, {}
    for a in range(1, 8):
        if a == 6:
            acts[a] = {"start": t, "duration": DEMO_LEN}
            t += DEMO_LEN
            continue
        lo, hi = ACT_SEGS[a]
        cur = LEAD
        for n in range(lo, hi + 1):
            seg_start[n] = t + cur
            cur += dur(natural(n)) + GAP
        length = float(-(-int(round((cur - GAP + (LAST_TAIL if a == 7 else TAIL)) * 100)) // 100))  # whole seconds, rounded up
        acts[a] = {"start": t, "duration": round(length, 2)}
        t += length
    return {"acts": acts, "seg_start": seg_start, "total": round(t, 2)}


def patch_index(s: dict) -> None:
    p = ROOT / "hyperframes_film" / "index.html"
    html = p.read_text(encoding="utf-8")
    for a, v in s["acts"].items():
        m = re.search(rf'id="act{a}".*?data-start="[\d.]+"\s*data-duration="[\d.]+"', html, re.S)
        block = re.sub(r'data-start="[\d.]+"', f'data-start="{v["start"]:.2f}"', m.group(0))
        block = re.sub(r'data-duration="[\d.]+"', f'data-duration="{v["duration"]:.2f}"', block)
        html = html.replace(m.group(0), block)
    html = re.sub(r'(id="root"[^>]*?data-duration=)"[\d.]+"', rf'\1"{s["total"]:.2f}"', html, flags=re.S)
    html = re.sub(r'duration: 1080, ease: "none"', f'duration: {s["total"]:.2f}, ease: "none"', html)
    html = html.replace("Progress Bar across 1080 seconds", f"Progress Bar across {s['total']:.0f} seconds")
    lines = ['      // Section Highlights (re-timed to narration)']
    for a in range(1, 8):
        st, en = s["acts"][a]["start"], s["acts"][a]["start"] + s["acts"][a]["duration"]
        lines.append(f'      tl.set("#nav-s{a}", {{ className: "nav-item active" }}, {st:.2f});')
        if a < 7:
            lines.append(f'      tl.set("#nav-s{a}", {{ className: "nav-item" }}, {en:.2f});')
    html = re.sub(r'      // Section Highlights.*?(?=\n\s*window\.__timelines)', "\n".join(lines) + "\n", html, flags=re.S)
    p.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sched = build()
    (OUT / "schedule.json").write_text(json.dumps(sched, indent=1), encoding="utf-8")
    patch_index(sched)
    for a, v in sched["acts"].items():
        print(f"act {a}: {v['start']:.1f}s +{v['duration']:.1f}s")
    print("total", sched["total"], "s =", round(sched["total"] / 60, 2), "min")
