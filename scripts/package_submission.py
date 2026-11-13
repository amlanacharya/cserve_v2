"""Build AmlanAcharya_Capstone_Submission.zip in the layout required by the Submission Guide.

Usage: python scripts/package_submission.py

01_Video      project_submission_full.mp4 (voiced film) and project_app_demo.mp4 (voiced in-app demo)
02_Report     the PDF report
03_Workbooks  five stage workbooks + effort log
04_Source_Code  tracked + untracked-but-not-ignored files, plus .git history; never .env or caches
"""
import argparse
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "AmlanAcharya"
OUT = ROOT / "04_Submission" / f"{NAME}_Capstone_Submission.zip"
SKIP_PREFIX = ("hyperframes_film/renders/", "hyperframes_film/.hyperframes/", "01_Video/", "04_Submission/")
SKIP_SUFFIX = (".mp4",)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.parse_args()

    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    files = [f for f in files if not f.startswith(SKIP_PREFIX) and not f.endswith(SKIP_SUFFIX) and Path(ROOT, f).is_file()]
    assert not any(f == ".env" or f.endswith("/.env") for f in files), "refusing to package .env"

    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("project_submission_full.mp4", "project_app_demo.mp4"):
            z.write(ROOT / "01_Video" / name, f"01_Video/{name}")
        z.write(ROOT / "02_Report" / f"{NAME}_Capstone_Report.pdf", f"02_Report/{NAME}_Capstone_Report.pdf")
        for wb in sorted((ROOT / "03_Workbooks").glob("*.docx")):
            z.write(wb, f"03_Workbooks/{wb.name}")
        for f in files:
            z.write(ROOT / f, f"04_Source_Code/{f}")
        git_dir = ROOT / ".git"
        for p in git_dir.rglob("*"):
            if p.is_file():
                z.write(p, f"04_Source_Code/.git/{p.relative_to(git_dir).as_posix()}")
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
