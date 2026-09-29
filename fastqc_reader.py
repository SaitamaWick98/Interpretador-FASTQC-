"""Lectura de módulos FastQC sin extraer archivos al disco."""
import zipfile
from pathlib import Path, PurePosixPath


def parse_fastqc_data(content: str) -> dict:
    """Conserva encabezados y valida los límites y estados de cada módulo."""
    modules = {}
    current = None
    status = None
    lines = []
    for number, line in enumerate(content.splitlines(), start=1):
        if line == ">>END_MODULE":
            if current is None:
                raise ValueError(f"Cierre sin módulo en la línea {number}.")
            modules[current] = {"status": status, "data": "\n".join(lines)}
            current = None
        elif line.startswith(">>"):
            if current is not None:
                raise ValueError(f"Módulo sin cerrar: {current}.")
            parts = line[2:].split("\t")
            if len(parts) != 2 or not parts[0] or parts[1] not in {"pass", "warn", "fail"}:
                raise ValueError(f"Encabezado de módulo inválido en la línea {number}.")
            current, status = parts
            if current in modules:
                raise ValueError(f"Módulo duplicado: {current}.")
            lines = []
        elif current is not None:
            lines.append(line)
        elif line and not line.startswith("##FastQC"):
            raise ValueError(f"Datos fuera de un módulo en la línea {number}.")
    if current is not None:
        raise ValueError(f"Módulo sin cerrar: {current}.")
    if not modules:
        raise ValueError("El informe no contiene módulos FastQC.")
    return modules


def read_fastqc_data(output_dir: Path) -> dict:
    """Lee únicamente ZIP de FastQC en la carpeta indicada, sin recursión."""
    archives = sorted(Path(output_dir).glob("*_fastqc.zip"))
    if not archives:
        raise ValueError(f"No hay informes *_fastqc.zip en {output_dir}.")
    results = {}
    for archive in archives:
        try:
            with zipfile.ZipFile(archive) as zf:
                members = [
                    item for item in zf.infolist()
                    if not item.is_dir() and PurePosixPath(item.filename).name == "fastqc_data.txt"
                ]
                if len(members) != 1:
                    raise ValueError("Se esperaba exactamente un archivo fastqc_data.txt.")
                content = zf.read(members[0]).decode("utf-8-sig")
            sample = archive.stem[:-len("_fastqc")]
            if sample in results:
                raise ValueError(f"Nombre de muestra duplicado: {sample}.")
            results[sample] = parse_fastqc_data(content)
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise ValueError(f"No se pudo leer {archive.name}: {exc}") from exc
    return results
