# Import required libraries
# 

import subprocess # is a library used to run system commands
import sys
import os
from pathlib import Path
import zipfile

# Run FastQC

def run_fastqc(*fastqc_files: str, output_dir: str = "fastqc_output") -> Path:

    output_path = Path(output_dir)

    # Verificamos la existencia de los archivos
    for f in fastqc_files:
        if not Path(f).exists():
            print(f"[ERROR :(]: {f} no existe :/")
            sys.exit(1)


    # Verificamos la existencia de la carpeta
    output_path.mkdir(exist_ok=True)


    # Comando a usar
    fastqc_comando = [
        "fastqc",
        *fastqc_files,
        "-o",
        str(output_path)
    ]

    result = subprocess.run(
        fastqc_comando,
        capture_output=True,
        text=True
    )

    # Verificar que no haya fallado
    if result.returncode != 0:
        print(f"[ERROR]: Fastqc no se ejectuto bien")
        print(result.stderr)
        sys.exit(1)

    print(f"[NICE] FastQC se ejecuto bien amigo mio")

    return output_path