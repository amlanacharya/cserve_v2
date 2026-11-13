"""Cut dead air out of a voiced video so no silence lasts longer than MAX_SILENCE seconds.

Usage: python scripts/tighten_silence.py in.mp4 out.mp4 [seam_time ...]

Audio and video are cut together, so lip-sync between narration and slides is preserved. A "seam" is a
time where a slide changes (an act start): the 1.0 s after it is kept in full so the slide's entrance
animation is never cut in half.
"""
import re
import subprocess
import sys
from pathlib import Path

NOISE_DB = -40
DETECT = 1.5  # only silences longer than this are touched
HEAD, TAIL_KEEP = 0.3, 0.1  # kept before a seam / after the entrance animation
SIDE = 0.55  # kept on each side of a cut that is not at a seam
SEAM_HOLD = 0.9  # entrance animation kept after a seam
FFMPEG = "ffmpeg"


def probe_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def silences(path: str, dur: float) -> list[tuple[float, float]]:
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-af",
                        f"silencedetect=n={NOISE_DB}dB:d={DETECT}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    if len(ends) < len(starts):
        ends.append(dur)
    return list(zip(starts, ends))


def cuts_for(s: float, e: float, seams: list[float]) -> list[tuple[float, float]]:
    seam = next((t for t in seams if s + 0.2 < t < e - 0.2), None)
    if seam is None:
        return [(s + SIDE, e - SIDE)] if e - s > 2 * SIDE + 0.05 else []
    out = []
    a, b = s + HEAD, seam
    if b - a > 0.05:
        out.append((a, b))
    a, b = seam + SEAM_HOLD, e - TAIL_KEEP
    if b - a > 0.05:
        out.append((a, b))
    return out


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    seams = [float(x) for x in sys.argv[3:]]
    dur = probe_duration(src)
    cuts = sorted(c for s, e in silences(src, dur) for c in cuts_for(s, e, seams))
    keep, pos = [], 0.0
    for a, b in cuts:
        if a > pos:
            keep.append((pos, a))
        pos = max(pos, b)
    if pos < dur:
        keep.append((pos, dur))
    removed = dur - sum(b - a for a, b in keep)
    print(f"{len(cuts)} cuts, {removed:.1f}s removed, {dur:.1f}s -> {dur - removed:.1f}s")

    parts = []
    for i, (a, b) in enumerate(keep):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]")
    cat = "".join(f"[v{i}][a{i}]" for i in range(len(keep)))
    parts.append(f"{cat}concat=n={len(keep)}:v=1:a=1[v][a]")
    script = Path(dst).with_suffix(".filter.txt")
    script.write_text(";\n".join(parts), encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-filter_complex_script", str(script),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst], check=True)
    script.unlink()
    print("wrote", dst)


if __name__ == "__main__":
    main()
