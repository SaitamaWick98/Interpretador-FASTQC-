import subprocess

resultado = subprocess.run(
	["ls"],
	capture_output=True,
	text=True
)

print(resultado.stdout)
