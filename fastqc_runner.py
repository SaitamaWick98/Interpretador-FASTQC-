"""Ejecución local de FastQC con resultados aislados por corrida."""
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_fastqc(*fastqc_files: str, output_dir: str = "fastqc_output") -> Path:
    """Valida entradas y devuelve una nueva carpeta con los informes."""
    if not fastqc_files:
        raise ValueError("Indica al menos un archivo FASTQ.")
    files = [Path(name).expanduser().resolve() for name in fastqc_files]
    for path in files:
        if not path.is_file():
            raise ValueError(f"No es un archivo existente: {path}")
        if path.stat().st_size == 0:
            raise ValueError(f"El archivo está vacío: {path}")
    names = set()
    for path in files:
        name = path.name
        for suffix in (".gz", ".bz2"):
            if name.lower().endswith(suffix):
                name = name[:-len(suffix)]
                break
        name = Path(name).stem.casefold()
        if name in names:
            raise ValueError(
                "Hay entradas que producirían el mismo nombre de informe. "
                "Usa nombres de muestra únicos o ejecuciones separadas."
            )
        names.add(name)
    executable = shutil.which("fastqc")
    if not executable:
        raise RuntimeError("No se encontró fastqc en PATH. Instálalo y verifica fastqc --version.")
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=str(root)))
    command = [executable, *map(str, files), "--noextract", "-o", str(run_dir)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    except OSError as exc:
        raise RuntimeError(f"No se pudo iniciar FastQC: {exc}") from exc
    (run_dir / "fastqc.stdout.log").write_text(result.stdout, encoding="utf-8")
    (run_dir / "fastqc.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(
            f"FastQC terminó con código {result.returncode}. "
            f"Consulta {run_dir / 'fastqc.stderr.log'}"
        )
    archives = list(run_dir.glob("*_fastqc.zip"))
    if len(archives) != len(files):
        raise RuntimeError(
            f"FastQC no generó un ZIP por entrada ({len(archives)}/{len(files)}). "
            f"Revisa los registros en {run_dir}."
        )
    return run_dir
