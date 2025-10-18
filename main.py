#!/usr/bin/env python3
"""
Punto de entrada legacy - Redirige a orchestrator.py
Este archivo se mantiene por compatibilidad con scripts antiguos.
"""

import sys
import subprocess

print("\n" + "="*70)
print("⚠️  ADVERTENCIA: main.py está deprecado")
print("="*70)
print("\nEste script ahora ejecuta 'orchestrator.py' automáticamente.")
print("Por favor, actualiza tus scripts para usar directamente:")
print("  python orchestrator.py")
print("\n" + "="*70 + "\n")

# Ejecutar orchestrator.py
sys.exit(subprocess.call([sys.executable, "orchestrator.py"]))
