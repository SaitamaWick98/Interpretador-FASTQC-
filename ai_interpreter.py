import os
import sys
from google import genai


def interpret_with_ai(resultados: dict) -> str:
    """
    Recibe el diccionario de resultados de FastQC y
    pide a Gemini que los interprete.
    """

    # Verificamos que la API key esté configurada
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] No se encontró GOOGLE_API_KEY en las variables de entorno")
        sys.exit(1)

    # Creamos el cliente de Gemini
    client = genai.Client(api_key=api_key)

    # Construimos el texto con los resultados de todas las muestras
    # para incluirlo en el prompt
    resumen = ""
    for muestra, modulos in resultados.items():
        resumen += f"\nMuestra: {muestra}\n"
        for modulo, info in modulos.items():
            resumen += f"  {info['status'].upper()}: {modulo}\n"
            resumen += f"  Datos:\n{info['data']}\n"

    # Construimos el prompt
    prompt = f"""Eres un bioinformático experto en control de calidad de datos de secuenciación.
Se te proporcionan los resultados de un análisis FastQC.

{resumen}

Por favor:
1. Interpreta cada módulo y explica qué significa biológica o técnicamente.
2. Da un veredicto final: ¿la muestra es APTA o NO APTA para continuar con el análisis?
3. Si hay problemas, sugiere pasos de preprocesamiento como Trimmomatic o fastp.
4. El resultado se mostrara en terminal asi que adapta un estilo de visualizacion sencillo y evita el markdown para que no se vean caracteres raros

Sé claro y conciso."""

    print("[INFO] Consultando a Gemini...")

    # Llamada a la API
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text