"""Place voiceover/seg_XX.wav on the film timeline and mux onto the silent videos.

    python scripts/assemble_voiceover.py

Outputs (01_Video/): hyperframes_presentation_18min_voiced.mp4 and in_app_demo_live_voiced.mp4.
Each segment is time-fitted to its window: sped up (max 1.15x) if it overruns, slowed (min 0.88x)
to use slack, so delivery stays natural. Overruns beyond the cap are reported, never truncated.
"""
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


def main() -> None:
    segs = parse_segments()
    film_v = VID / "hyperframes_presentation_18min.mp4"
    demo_v = VID / "in_app_demo_live.mp4"
    p1 = build_track(segs, 0, duration(film_v), OUT / "narration_full.wav")
    mux(film_v, OUT / "narration_full.wav", VID / "hyperframes_presentation_18min_voiced.mp4")
    demo = [s for s in segs if 750 <= s["start"] < 960]  # Act VI is the live demo
    p2 = build_track(demo, 750, duration(demo_v), OUT / "narration_demo.wav")
    mux(demo_v, OUT / "narration_demo.wav", VID / "in_app_demo_live_voiced.mp4")
    for p in p1 + p2:
        print("WARN", p)
    print("done", "with warnings" if p1 + p2 else "clean")


if __name__ == "__main__":
    main()
