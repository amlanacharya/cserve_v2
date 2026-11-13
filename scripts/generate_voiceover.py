"""Clone the presenter's voice (Chatterbox, local GPU) and narrate hyperframes_film/DIRECTOR_SCRIPT.md.

Run with the voice environment, not the project venv:
    C:/Users/amlan/chatterbox_env/Scripts/python.exe scripts/generate_voiceover.py --only 1
    ... --all            # every segment, then assemble voiceover/narration_full.wav

Each `> *(m:ss - m:ss)* "text"` line is one segment. Audio is written to 01_Video/voiceover/seg_XX.wav
and the report lists any segment longer than its time window.
"""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "hyperframes_film" / "DIRECTOR_SCRIPT.md"
OUT = ROOT / "01_Video" / "voiceover"
REF = ROOT / "01_Video" / "voice_sample_clean.wav"

# Spoken forms for terms a TTS model would mangle. Order matters (longest first).
PRONOUNCE = [
    (r"\bdecision_log_no_update\b", "decision log no update"),
    (r"\bChromaDB\b", "Chroma D B"),
    (r"\bLangGraph\b", "Lang Graph"),
    (r"\bSQLite\b", "S Q Lite"),
    (r"\bFastAPI\b", "Fast A P I"),
    (r"\bPytest\b", "Pie test"),
    (r"\bP95\b", "P ninety-five"),
    (r"\bECE\b", "E C E"),
    (r"\bFCR\b", "F C R"),
    (r"\bPII\b", "P I I"),
    (r"\bAPI\b", "A P I"),
    (r"\bCLI\b", "C L I"),
    (r"\bSHA-256\b", "S H A two fifty-six"),
    (r"\bLuhn\b", "Loon"),
    (r"\bGroq\b", "Grok"),
    (r"\bUPDATE\b", "update"),
    (r"\bDOC-([A-Z]+)-(\d+)\b", lambda m: f"doc {m.group(1)} {int(m.group(2))}"),
]


def speakable(text: str) -> str:
    text = re.sub(r"\*+|`", "", text)
    text = re.sub(r"\[(DOC-[A-Z0-9-]+)\]", r"\1", text)
    for pat, rep in PRONOUNCE:
        text = re.sub(pat, rep, text)
    text = re.sub(r"(\d+(?:\.\d+)?)%", r"\1 per cent", text)
    text = text.replace("&bull;", ",").replace("—", ", ").replace("–", " to ")
    return re.sub(r"\s+", " ", text).strip()


def to_seconds(stamp: str) -> int:
    m, s = stamp.strip().split(":")
    return int(m) * 60 + int(s)


def parse_segments() -> list[dict]:
    segs = []
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*>\s*\*\((\d+:\d+)\s*[-–]\s*(\d+:\d+)\)(?:\s*\[[^\]]*\])?\*?\s*"(.*)"\s*$', line)
        if m:
            segs.append({"start": to_seconds(m[1]), "end": to_seconds(m[2]), "text": speakable(m[3])})
    for i, s in enumerate(segs, 1):
        s["n"] = i
    return segs


def chunks(text: str, limit: int = 260) -> list[str]:
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?:;])\s+", text):
        if cur and len(cur) + len(sent) > limit:
            out.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    return out + ([cur] if cur else [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*", help="segment numbers")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--exaggeration", type=float, default=0.45)
    ap.add_argument("--cfg", type=float, default=0.5)
    a = ap.parse_args()
    segs = parse_segments()
    todo = segs if a.all else [s for s in segs if s["n"] in (a.only or [1])]
    OUT.mkdir(parents=True, exist_ok=True)

    import torch
    import soundfile as sf
    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_pretrained(device="cuda")
    gap = torch.zeros(1, int(0.30 * model.sr))
    for s in todo:
        torch.manual_seed(7)
        parts = []
        for c in chunks(s["text"]):
            wav = model.generate(c, audio_prompt_path=str(REF), exaggeration=a.exaggeration, cfg_weight=a.cfg)
            parts += [wav.cpu(), gap]
        audio = torch.cat(parts, dim=1)
        path = OUT / f"seg_{s['n']:02d}.wav"
        sf.write(str(path), audio.squeeze(0).numpy(), model.sr)
        dur, window = audio.shape[1] / model.sr, s["end"] - s["start"]
        flag = "OVER" if dur > window else "ok"
        print(f"seg {s['n']:02d} [{s['start']}-{s['end']}s] speech {dur:5.1f}s / window {window}s  {flag}")


if __name__ == "__main__":
    main()
