"""Interfaz de FastQC y su interpretación opcional."""
import argparse
import json
import sys

from ai_interpreter import AIError, DEFAULT_MODEL, interpret_with_ai
from fastqc_reader import read_fastqc_data
from fastqc_runner import run_fastqc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ejecuta FastQC y genera un reporte local con interpretación opcional de Gemini.",
        epilog="Un código 0 indica ejecución correcta, no aprobación de la calidad de las muestras.",
    )
    parser.add_argument("files", nargs="+", metavar="FASTQ", help="Archivos de entrada para FastQC.")
    parser.add_argument("-o", "--output", default="fastqc_output", metavar="DIR",
                        help="Carpeta base de salida; se crea una subcarpeta única por ejecución.")
    parser.add_argument("--no-ai", action="store_true", help="Modo local sin SDK, clave ni consulta a Gemini.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modelo Gemini (predeterminado: %(default)s).")
    return parser


def quality_report(results: dict) -> str:
    lines = ["REPORTE DE CALIDAD", ""]
    for sample, modules in results.items():
        lines.append(f"Muestra: {sample}")
        for module, info in modules.items():
            lines.append(f"  {info['status'].upper()}: {module}")
        lines.append("")
    lines.append("Los estados por módulo no determinan por sí solos la aptitud de una muestra.")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_dir = run_fastqc(*args.files, output_dir=args.output)
        print(f"Resultados: {run_dir}")
        results = read_fastqc_data(run_dir)
        (run_dir / "results.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        report = quality_report(results)
        report_path = run_dir / "reporte.txt"
        report_path.write_text(report, encoding="utf-8")
        print(report)
        if args.no_ai:
            print("Modo local: no se enviaron datos a Gemini.")
            return 0
        print("Consultando a Gemini: se enviarán los nombres y los datos de los módulos.")
        try:
            interpretation = interpret_with_ai(results, model=args.model)
        except AIError as exc:
            report_path.write_text(report + f"\nINTERPRETACIÓN NO DISPONIBLE\n{exc}\n", encoding="utf-8")
            print(f"[ERROR IA] {exc}\nResultados locales conservados en {run_dir}", file=sys.stderr)
            return 3
        section = "\nINTERPRETACIÓN ORIENTATIVA POR IA\n\n" + interpretation + "\n"
        report_path.write_text(report + section, encoding="utf-8")
        print(section)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nEjecución interrumpida.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
