Resumen rápido
Puedes subir archivos generados en memoria directamente a Supabase Storage desde Python sin guardarlos en disco usando la librería oficial supabase-py (o cualquier cliente HTTP) enviando el contenido como bytes. A continuación te doy 3 opciones claras y completas: (A) ejemplo con supabase-py, (B) usando requests (HTTP directo), y (C) subir un archivo de imagen generado en memoria (PIL) — todas sin escribir en disco.
A — Usando supabase-py (recomendado si ya lo usas)
Requisitos:

pip install supabase
Tener SUPABASE_URL y SUPABASE_ANON_KEY (o SERVICE_ROLE si necesitas evadir RLS; evita service role en clientes públicos).
Ejemplo (subida de bytes en memoria):
from supabase import create_client
import io

SUPABASE_URL = "https://xyz.supabase.co"
SUPABASE_KEY = "public-anon-or-service-key"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Contenido generado en memoria (bytes). Ejemplo: texto
content = "Hola desde memoria!".encode("utf-8")
buffer = io.BytesIO(content)

bucket = "mi-bucket"
remote_path = "carpeta/archivo.txt"

# supabase-py espera un objeto file-like o bytes. Usamos buffer.getvalue()
res = supabase.storage.from_(bucket).upload(remote_path, buffer.getvalue(), {"content-type": "text/plain"})

print(res)  # la librería devuelve dict con status / error
Notas:

Para archivos binarios (imágenes, pdf), usa content-type apropiado (e.g., "image/png").
Si el archivo existe y quieres reemplazar, elimina primero o maneja el error según la respuesta.