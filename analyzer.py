import sys
from pathlib import Path

from fastqc_runner import run_fastqc
from fastqc_reader import read_fastqc_data
from ai_interpreter import interpret_with_ai

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Uso: python3 analyzer.py <archivo1.fastq> <archivo2.fastq> ...")
        sys.exit(1)

    fastq_files = sys.argv[1:]

    # ── Paso 1: Correr FastQC ──
    output_dir = run_fastqc(*fastq_files)

    # ── Paso 2: Leer resultados ──
    resultados = read_fastqc_data(output_dir)

    # ── Paso 3: Imprimir reporte ──
    print("\n══════════════════════════════════")
    print("        REPORTE DE CALIDAD        ")
    print("══════════════════════════════════")

    for muestra, modulos in resultados.items():
        print(f"\n🧬 Muestra: {muestra}")
        print("──────────────────────────────────")
        for modulo, info in modulos.items():
            print(f"  {info['status'].upper()}: {modulo}")

    # ── Paso 4: Interpretar con IA ──
    interpretacion = interpret_with_ai(resultados)

    print("\n══════════════════════════════════")
    print("      INTERPRETACIÓN POR IA       ")
    print("══════════════════════════════════\n")
    print(interpretacion)