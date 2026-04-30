import zipfile
from pathlib import Path
import sys

# Funcion para encontrar los archivos zip
def read_fastqc_data(output_dir: Path) -> dict:

    output_path = Path(output_dir)

    # Buscar los archivos zip
    zip_files = list(output_path.glob("*.zip"))

    if not zip_files:
        print(f"[Error] No se identificaron archivos zip en {output_dir}")
        sys.exit(1)

    resultados = {}

    for zip_file in zip_files:
        print(zip_file)

        # Abrir el zip
        with zipfile.ZipFile(zip_file, "r") as zf:

            # Construimos el nombre de la carpeta adentro del zip
            # Ejemplo: SRR1972739_fastqc.zip → SRR1972739_fastqc
            sample_folder = zip_file.stem

            # Construimos la ruta al fastqc_data.txt adentro del zip
            data_path = f"{sample_folder}/fastqc_data.txt"

            # Abrimos el archivo directamente desde el zip
            with zf.open(data_path) as f:
                contenido = f.read().decode("utf-8")

            # Nombre de la muestra sin _fastqc
            # Ejemplo: SRR1972739_fastqc → SRR1972739
            sample_name = sample_folder.replace("_fastqc", "")

            # Diccionario donde guardaremos los módulos de esta muestra
            modules = {}

            # Variables para rastrear en qué módulo estamos
            current_module = None   # nombre del módulo actual
            current_status = None   # pass, warn o fail
            current_data = []       # líneas de datos del módulo actual

            # Recorremos el contenido línea por línea
            for line in contenido.splitlines():

                # ── ¿Es inicio de módulo? ──
                if line.startswith(">>") and not line.startswith(">>END_MODULE"):
                    parts = line[2:].split("\t")
                    current_module = parts[0]
                    current_status = parts[1]
                    current_data = []

                # ── ¿Es fin de módulo? ──
                elif line.startswith(">>END_MODULE"):
                    if current_module:
                        modules[current_module] = {
                            "status": current_status,
                            "data": "\n".join(current_data)
                        }

                # ── ¿Es encabezado de columnas? ──
                elif line.startswith("#"):
                    pass   # lo ignoramos

                # ── Son datos normales ──
                else:
                    if current_module:
                        current_data.append(line)

            # Guardamos esta muestra en el diccionario principal
            resultados[sample_name] = modules

    return resultados  # ← fuera del for, devuelve todo al final