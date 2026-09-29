# Interpretador de FastQC

Ejecuta FastQC sobre uno o varios archivos de secuenciación, guarda un reporte de calidad y permite solicitar una interpretación orientativa a Gemini.

**La calidad de una muestra depende del experimento y del análisis posterior.** Los estados de FastQC y el texto de IA no constituyen una aprobación automática.

## Inicio rápido

Requisitos previos: Python 3 y FastQC accesible desde la terminal, con Java compatible.

Desde la raíz del repositorio:

```bash
python3 analyzer.py example_data/SRR1972739.fastq --no-ai
```

Este modo funciona localmente y no necesita clave, conexión a Gemini ni paquetes Python externos. Cada ejecución guarda sus resultados en una carpeta nueva dentro de `fastqc_output/`.

Para consultar las opciones:

```bash
python3 analyzer.py --help
```

## Instalación

### 1. Obtener el proyecto

```bash
git clone https://github.com/SaitamaWick98/Interpretador-FASTQC-.git
cd Interpretador-FASTQC-
```

También puedes descargar el repositorio como ZIP, descomprimirlo y abrir su carpeta.

### 2. Instalar FastQC y Java

Descarga FastQC desde su [sitio oficial](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/) y sigue las [instrucciones de instalación](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/INSTALL.txt). Instala Java compatible con la distribución elegida.

En macOS o Linux, para utilizar la distribución ZIP de línea de comandos, descomprímela y habilita su lanzador. Sustituye la ruta siguiente por la ubicación real:

```bash
chmod +x "/ruta/a/FastQC/fastqc"
export PATH="/ruta/a/FastQC:$PATH"
java -version
fastqc --version
```

El cambio de `PATH` afecta a esa terminal. Tener la aplicación gráfica no garantiza que el comando esté disponible. Los ejemplos de esta guía están escritos para Bash o Zsh; Windows nativo no se ha validado.

### 3. Preparar Python

```bash
python3 -m venv .venv
source .venv/bin/activate
```

El modo local solo utiliza la biblioteca estándar. Para Gemini instala la dependencia opcional:

```bash
python -m pip install -r requirements.txt
```

Para una instalación nueva con Gemini, utiliza Python 3.10 o superior y comprueba los requisitos de la versión del [SDK de Google](https://github.com/googleapis/python-genai) instalada. Las pruebas locales de esta copia se ejecutaron con Python 3.9.6, sin el SDK.

`requirements.txt` es el archivo principal; `requeriments.txt` se conserva como enlace de compatibilidad mediante `-r requirements.txt`. La dependencia `google-genai` aún no tiene una versión fijada ni un archivo de bloqueo.

### 4. Configurar Gemini (opcional)

El código lee únicamente `GOOGLE_API_KEY`. Para introducirla sin escribir su valor literalmente en el historial de comandos:

```bash
export GOOGLE_API_KEY="$(python -c 'import getpass; print(getpass.getpass("Clave de Gemini: "))')"
```

No guardes la clave en el código ni en el repositorio. El programa no carga archivos `.env` automáticamente.

Si no se indica `--no-ai`, se intenta consultar Gemini después de guardar el reporte local. Se conserva este comportamiento por compatibilidad con el comando original.

## Dependencias

| Componente | Uso |
|---|---|
| Python | Interfaz, lectura de ZIP y reportes. |
| FastQC y Java | Control de calidad local. |
| `google-genai` | Solo para la interpretación con Gemini. |
| Internet y `GOOGLE_API_KEY` | Solo para consultar Gemini. |
| Git | Descarga y seguimiento de versiones; no se necesita para ejecutar una copia descomprimida. |

## Uso

### Análisis local

```bash
python analyzer.py example_data/SRR1972739.fastq --no-ai
```

### Con Gemini

```bash
python analyzer.py example_data/SRR1972739.fastq
```

El modelo predeterminado es `gemini-2.5-flash`. Puedes cambiarlo por un identificador disponible en tu cuenta:

```bash
python analyzer.py example_data/SRR1972739.fastq --model ID_DEL_MODELO
```

### Varios archivos o lecturas pareadas

```bash
python analyzer.py datos/muestra_R1.fastq datos/muestra_R2.fastq --no-ai
```

Sustituye las rutas por archivos reales. R1 y R2 se analizan por separado: no se comprueba la correspondencia entre lecturas.

### Otra carpeta de salida

```bash
python analyzer.py "mis datos/muestra.fastq" --no-ai --output fastqc_output/experimento_1
```

La carpeta indicada es una **base de salida**; se crea dentro una subcarpeta `run-...` distinta por ejecución. No se sobrescriben ni se mezclan informes previos.

| Argumento | Función |
|---|---|
| `FASTQ [FASTQ ...]` | Una o varias rutas de entrada. |
| `--no-ai` | No importa el SDK ni consulta Gemini. |
| `-o DIR`, `--output DIR` | Carpeta base; predeterminada: `fastqc_output`. |
| `--model NOMBRE` | Modelo de Gemini; no tiene efecto con `--no-ai`. |
| `-h`, `--help` | Ayuda y sintaxis. |

## Formato de entrada

El archivo incluido es FASTQ sin comprimir. Cada registro convencional contiene un identificador, una secuencia, un separador y las calidades:

```text
@lectura_1
ACGTACGT
+
IIIIIIII
```

La secuencia y las calidades deben tener la misma longitud. FastQC valida el contenido; el programa comprueba que las rutas sean archivos existentes y no vacíos. Los formatos adicionales y la compresión dependen de FastQC.

No pases carpetas, HTML ni ZIP de resultados como entradas al comando principal. Utiliza comillas si las rutas contienen espacios. Se rechazan entradas que producirían nombres de informe coincidentes, por ejemplo `muestra.fastq` y `muestra.fastq.gz`.

## Ejecución con los datos incluidos

Con FastQC instalado y desde la raíz del proyecto:

```bash
python analyzer.py example_data/SRR1972739.fastq --no-ai
```

La terminal muestra la ubicación exacta de los resultados. Allí encontrarás:

```text
fastqc_output/
└── run-<identificador>/
    ├── SRR1972739_fastqc.html
    ├── SRR1972739_fastqc.zip
    ├── fastqc.stdout.log
    ├── fastqc.stderr.log
    ├── results.json
    └── reporte.txt
```

Los archivos HTML y ZIP los produce FastQC. `results.json` contiene los módulos, sus estados y los datos con encabezados. `reporte.txt` contiene el resumen y, cuando se solicita y está disponible, la interpretación con IA.

No se publica un veredicto esperado: esta revisión no ejecutó FastQC real sobre la muestra. El repositorio de origen tampoco documenta cómo se obtuvo o preparó el archivo ni si es un subconjunto de datos.

Para registrar tu entorno después de una ejecución:

```bash
{
  python --version
  fastqc --version
  java -version
  python -m pip freeze
} > versiones.txt 2>&1
```

Si utilizas una copia Git, registra además `git rev-parse HEAD` y cualquier cambio local. Registrar versiones facilita repetir el procedimiento; las dependencias no fijadas y las respuestas variables de IA impiden prometer resultados idénticos.

## Interpretación y códigos de salida

`PASS`, `WARN` y `FAIL` son los estados de los módulos de FastQC. No se convierten automáticamente en un veredicto global.

| Código | Significado |
|---|---|
| `0` | Se completó el flujo solicitado; no implica que la muestra tenga buena calidad. |
| `1` | Error local: entradas, FastQC, lectura o escritura. |
| `2` | Argumentos de línea de comandos inválidos. |
| `3` | El reporte local se guardó, pero la interpretación con IA no se completó. |
| `130` | Ejecución interrumpida por el usuario. |

Si Gemini falla, se conservan los resultados locales y el motivo se anota en `reporte.txt`. Los mensajes del proveedor no se imprimen completos para evitar exponer credenciales o datos.

## Estructura

```text
Interpretador-FASTQC-/
├── analyzer.py             # Interfaz y coordinación
├── fastqc_runner.py        # Validación y ejecución aislada de FastQC
├── fastqc_reader.py        # Lectura y validación de módulos
├── ai_interpreter.py       # Interpretación opcional de Gemini
├── requirements.txt        # Dependencia opcional principal
├── requeriments.txt        # Compatibilidad con el nombre anterior
├── args_example.py         # Ejercicio independiente de *args
├── subprocess_example.py   # Ejercicio independiente de subprocess
├── sys_example.py          # Ejercicio independiente de sys.argv
├── example_data/
│   └── SRR1972739.fastq
├── tests/
│   └── test_pipeline.py
├── .gitignore
└── README.md
```

Los scripts `*_example.py` son ejercicios y no participan en el análisis. `args_example.py` imprime `15`; las opciones reales se definen con `argparse` en `analyzer.py`.

## Pruebas

Desde la raíz:

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas utilizan datos sintéticos, una API simulada y un ejecutable simulado de FastQC. Comprueban aislamiento de resultados, encabezados, ZIP dañados, entradas inválidas, colisiones de nombres, reportes guardados, fallos de IA y el modo sin SDK. No realizan llamadas de red ni consumen cuota.

Pasar estas pruebas no sustituye una ejecución de integración con Java, FastQC y Gemini reales.

## Datos enviados a Gemini

Con IA habilitada se envían los nombres de las muestras y el contenido de los módulos, incluidos los encabezados. No se adjunta el FASTQ completo, pero algunos módulos pueden contener secuencias sobrerrepresentadas. Usa `--no-ai` cuando el análisis deba permanecer local.

La interpretación es orientativa y no ejecuta recorte, filtrado ni otras recomendaciones.

## Limitaciones y solución de problemas

- **Servicio externo:** la disponibilidad del modelo, las cuotas y los errores de conexión dependen de Google. Revisa estos factores o usa `--no-ai`.
- **Tamaño de la solicitud:** se aplica un límite local de 200 000 caracteres; no equivale a un límite de tokens del proveedor. Si se supera, divide las muestras en ejecuciones menores.
- **Memoria:** los informes se leen completos y se reúnen en una sola solicitud; no hay procesamiento por bloques.
- **FastQC ausente:** comprueba `fastqc --version` y el `PATH`.
- **FastQC falla:** consulta los archivos de registro de la nueva carpeta. Los resultados parciales se conservan para diagnóstico.
- **ZIP inválido:** se espera exactamente un `fastqc_data.txt` por ZIP. Se conserva el contenido de las tablas y se rechazan módulos mal formados.
- **Pares:** no se sincronizan ni se validan R1/R2 entre sí.
- **Configuración:** no se exponen todas las opciones de FastQC ni existe un modo CLI para reutilizar ZIP anteriores.
- **Compatibilidad:** no hay matriz de versiones validada ni dependencias bloqueadas. La ejecución real con FastQC y Gemini está pendiente de comprobarse en un entorno con esas dependencias.
- **Archivos locales:** `.gitignore` excluye el entorno virtual, claves en `.env` y la salida predeterminada. Si eliges otra carpeta de salida fuera de ella, añade su ruta a `.gitignore` antes de publicar.

## Licencia

El repositorio de origen no incluye una licencia. Esta revisión no añade ni presupone permisos de uso o redistribución.
