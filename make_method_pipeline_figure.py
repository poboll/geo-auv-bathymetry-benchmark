from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LATEX_PIC = ROOT / "manuscript" / "latex" / "pic"
MDPI_PIC = ROOT / "manuscript" / "mdpi_jmse" / "pic"
SOURCE = LATEX_PIC / "method_pipeline.tex"
PDF = LATEX_PIC / "method_pipeline.pdf"
PNG = LATEX_PIC / "method_pipeline_preview.png"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    run(["xelatex", "-interaction=nonstopmode", SOURCE.name], LATEX_PIC)

    MDPI_PIC.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PDF, MDPI_PIC / "method_pipeline.pdf")
    shutil.copy2(SOURCE, MDPI_PIC / "method_pipeline.tex")

    # Optional raster preview for quick visual QA in the Codex app.
    if shutil.which("gs"):
        run(
            [
                "gs",
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-sDEVICE=png16m",
                "-r220",
                f"-sOutputFile={PNG.name}",
                PDF.name,
            ],
            LATEX_PIC,
        )


if __name__ == "__main__":
    main()
