"""Place voiceover/seg_XX.wav on the film timeline and mux onto the silent videos.

    python scripts/assemble_voiceover.py

Outputs (01_Video/): project_submission_full.mp4 and project_app_demo.mp4 (dead air over 1.5 s cut by tighten_silence.py).
Each segment is time-fitted to its window: sped up (max 1.15x) if it overruns, slowed (min 0.88x)
to use slack, so delivery stays natural. Overruns beyond the cap are reported, never truncated.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_voiceover import OUT, ROOT, parse_segments  # noqa: E402

VID = ROOT / "01_Video"
FILM_START_PAD = 0.4  # seconds of room before a segment starts
MIN_T, MAX_T = 0.88, 1.15


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def fit(seg: dict) -> tuple[Path, float]:
    src = OUT / f"seg_{seg['n']:02d}.wav"
    window = seg["end"] - seg["start"] - 0.6
    raw = duration(src)
    tempo = min(MAX_T, max(MIN_T, raw / window))  # >1 speeds up
    dst = OUT / f"fit_{seg['n']:02d}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"silenceremove=stop_periods=-1:stop_duration=0.9:stop_threshold=-45dB,atempo={tempo:.4f}", str(dst)], check=True)
    print(f"seg {seg['n']:02d} tempo {tempo:.2f}")
    return dst, raw / tempo


def mix(items: list[tuple[Path, float]], total: float, out: Path) -> None:
    inputs, filters, labels = [], [], []
    for i, (wav, start) in enumerate(items):
        inputs += ["-i", str(wav)]
        ms = int(start * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    graph = f"{''.join(labels)}amix=inputs={len(items)}:normalize=0,loudnorm=I=-16:TP=-1.5,apad=whole_dur={total},atrim=0:{total}[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters + [graph]), "-map", "[out]", "-ar", "48000", str(out)], check=True)


def build_track(segs: list[dict], origin: int, total: float, out: Path) -> list[str]:
    inputs, filters, labels, problems = [], [], [], []
    for i, s in enumerate(segs):
        dst, dur = fit(s)
        window = s["end"] - s["start"]
        if dur > window:
            problems.append(f"seg {s['n']} still {dur:.1f}s in a {window}s window")
        inputs += ["-i", str(dst)]
        ms = int((s["start"] - origin + FILM_START_PAD) * 1000)
        filters.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
        labels.append(f"[a{i}]")
    mix = f"{''.join(labels)}amix=inputs={len(segs)}:normalize=0,loudnorm=I=-16:TP=-1.5,apad=whole_dur={total},atrim=0:{total}[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filters + [mix]), "-map", "[out]", "-ar", "48000", str(out)], check=True)
    return problems


def mux(video: Path, audio: Path, out: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{duration(video):.3f}", str(out)], check=True)


def pii_text() -> list[str]:
    """Real normalizer output for the demo's PII ticket (src/templates/dashboard.html, DEMO-PII-01)."""
    sys.path.insert(0, str(ROOT))
    from src.ingest.normalizer import normalize_ticket_with_stats

    raw = {"ticket_id": "DEMO-PII-01", "channel": "chat", "customer_id": "cust_billing_44",
           "body": "My corporate Visa card 4532015012345671 failed renewal on secret API key "
                   "cs_live_9a8b7c6d5e4f3a2b1c0d9e8f. Please review account."}
    canon, n = normalize_ticket_with_stats(raw)
    assert "[REDACTED_CC]" in canon.body and "[REDACTED_API_KEY]" in canon.body and n == 2, canon.body
    return [canon.body, f"{n} items redacted before any model call"]


def add_pii_caption(src: Path, dst: Path, t0: float, t1: float, film: bool) -> None:
    body, count = pii_text()
    font = "consola.ttf"  # copied next to the caption files: drive-letter colons break ffmpeg filter parsing
    enable = f"enable='between(t,{t0},{t1})'"
    work = OUT / "caption"
    work.mkdir(exist_ok=True)
    shutil.copy("C:/Windows/Fonts/consola.ttf", work / font)
    if film:  # white callout over the page subtitle strip (free space in the film layout)
        (work / "l1.txt").write_text("REDACTED ON INGEST  (normalizer output for this ticket, as stored)", encoding="utf-8")
        (work / "l2.txt").write_text(body, encoding="utf-8")
        (work / "l3.txt").write_text(count, encoding="utf-8")
        vf = (f"drawbox=x=60:y=168:w=1500:h=54:color=white@1:t=fill:{enable},"
              f"drawbox=x=60:y=168:w=1500:h=54:color=0x1d4ed8@1:t=2:{enable},"
              f"drawtext=fontfile={font}:textfile=l1.txt:x=74:y=174:fontsize=15:fontcolor=0x1d4ed8:{enable},"
              f"drawtext=fontfile={font}:textfile=l2.txt:x=74:y=194:fontsize=18:fontcolor=0x0f172a:{enable}")
    else:  # dark callout in the empty area under the ticket form
        import textwrap
        (work / "d.txt").write_bytes(("REDACTED ON INGEST\n(normalizer output, as stored)\n" + "\n".join(textwrap.wrap(body, 36)) + "\n" + count).encode("utf-8"))
        vf = (f"drawbox=x=139:y=852:w=414:h=176:color=0x0b1220@1:t=fill:{enable},"
              f"drawbox=x=139:y=852:w=414:h=176:color=0x38bdf8@1:t=2:{enable},"
              f"drawtext=fontfile={font}:textfile=d.txt:x=155:y=864:fontsize=14:line_spacing=5:fontcolor=0xe2e8f0:{enable}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(dst)], check=True, cwd=work)


def main() -> None:
    import json
    segs = parse_segments()
    sched = json.loads((OUT / "schedule.json").read_text(encoding="utf-8"))
    film_v = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "hyperframes_film/renders/film_retimed.mp4"
    demo_v = ROOT / "hyperframes_film/assets/in_app_demo.mp4"
    act6 = sched["acts"]["6"]["start"]
    items = [(OUT / f"nat_{int(n):02d}.wav", t) for n, t in sched["seg_start"].items()]
    p1 = []
    for sgm in (x for x in segs if 750 <= x["start"] < 960):  # demo narration follows the on-screen scenario marks
        dst, d = fit(sgm)
        if d > sgm["end"] - sgm["start"]:
            p1.append(f"seg {sgm['n']} overruns its scene")
        items.append((dst, act6 + sgm["start"] - 750 + FILM_START_PAD))
    total = duration(film_v)
    mix(items, total, OUT / "narration_full.wav")
    mux(film_v, OUT / "narration_full.wav", OUT / "film_nocap.mp4")
    demo = [s for s in segs if 750 <= s["start"] < 960]  # Act VI is the live demo
    p2 = build_track(demo, 750, duration(demo_v), OUT / "narration_demo.wav")
    mux(demo_v, OUT / "narration_demo.wav", OUT / "demo_nocap.mp4")
    import json
    marks = {m["id"]: m for m in json.loads((ROOT / "hyperframes_film/assets/in_app_demo.marks.json").read_text())["marks"]}
    t0, t1 = marks["pii"]["start"] + 4, marks["pii"]["end"] - 0.5  # after the result has rendered
    add_pii_caption(OUT / "demo_nocap.mp4", OUT / "demo_cap.mp4", t0, t1, film=False)
    add_pii_caption(OUT / "film_nocap.mp4", OUT / "film_cap.mp4", act6 + t0, act6 + t1, film=True)
    import subprocess
    tight = ROOT / "scripts" / "tighten_silence.py"
    seams = [str(v["start"]) for v in sched["acts"].values()]
    subprocess.run([sys.executable, str(tight), str(OUT / "demo_cap.mp4"), str(VID / "project_app_demo.mp4")], check=True)
    subprocess.run([sys.executable, str(tight), str(OUT / "film_cap.mp4"), str(VID / "project_submission_full.mp4"), *seams], check=True)
    for p in p1 + p2:
        print("WARN", p)
    print("done", "with warnings" if p1 + p2 else "clean")


if __name__ == "__main__":
    main()
