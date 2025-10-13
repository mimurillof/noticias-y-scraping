Claro que sí. Usar la API oficial de Reddit con PRAW es la forma correcta de hacerlo. Es más estable, eficiente y respetuosa con la plataforma.

Aquí tienes un tutorial completo, desde la obtención de las credenciales hasta el código Python final, diseñado para buscar tanto publicaciones populares ("hot") como menciones recientes de los activos de tu portafolio.

-----

### **Tutorial: Extracción de Datos de Reddit con PRAW para Inversores**

Este tutorial te guiará para configurar y utilizar la API de Reddit y así monitorear subreddits financieros.

#### **Paso 1: Obtener tus Credenciales de la API de Reddit 🔑**

Antes de escribir código, necesitas registrar una "aplicación" en Reddit para obtener tus claves de acceso. **Es gratis y toma dos minutos.**

1.  **Inicia sesión en Reddit** con la cuenta que usarás para el script.

2.  **Ve a la página de preferencias de aplicaciones:** [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)

3.  **Haz clic en el botón que dice "¿eres un desarrollador? crea una aplicación..."** en la parte inferior izquierda.

4.  **Rellena el formulario:**

      * **name:** Dale un nombre único a tu script (ej: `Monitor_Financiero_Miguel`).
      * **tipo de app:** Selecciona **`script`**.
      * **description:** Puedes dejarlo en blanco o poner una breve descripción.
      * **about url:** Puedes dejarlo en blanco.
      * **redirect uri:** Escribe `http://localhost:8080` (es un requisito, aunque no lo usaremos).
      * Haz clic en **`create app`**.

5.  **¡Guarda tus credenciales\!** Una vez creada, verás tu aplicación en la lista.

      * El **`client ID`** es la cadena de texto debajo del nombre de tu app.
      * El **`client secret`** es la cadena de texto junto a la etiqueta `secret`.
      * **Trata el `client secret` como una contraseña. No lo compartas.**

-----

### **Paso 2: Configurar el Entorno de Python 🐍**

Ahora, instalemos la librería PRAW (Python Reddit API Wrapper).

```bash
pip install praw
```

-----

### **Paso 3: El Código Python 📈**

Este script se conectará a la API, buscará publicaciones en los subreddits definidos y guardará los resultados en un archivo CSV.

Copia y pega este código en un archivo llamado `reddit_monitor.py`. **Recuerda rellenar tus credenciales en las primeras líneas.**

```python
import praw
import csv
import datetime

# --- CONFIGURACIÓN INICIAL (RELLENA TUS DATOS AQUÍ) ---

# 1. Rellena tus credenciales obtenidas en el Paso 1
CLIENT_ID = "TU_CLIENT_ID"
CLIENT_SECRET = "TU_CLIENT_SECRET"
USER_AGENT = "script:PortfolioMonitor:v1.0 (by u/TU_USUARIO_DE_REDDIT)" # Cambia TU_USUARIO

# 2. Define los activos de tu portafolio (nombres, tickers, etc.)
#    El script buscará menciones de estas palabras clave.
PORTFOLIO_ASSETS = [
    'Apple', 'AAPL', 'Nvidia', 'NVDA', 'Tesla', 'TSLA', 
    'Bitcoin', 'BTC', 'Ethereum', 'ETH', 'AMD', 'Google', 'GOOGL'
]

# 3. Define los subreddits que quieres monitorear
TARGET_SUBREDDITS = [
    'investing',
    'wallstreetbets',
    'stocks',
    'options',
    'trading',
    'CryptoCurrency'
]

# --- LÓGICA DEL SCRIPT ---

def initialize_reddit():
    """Inicializa y devuelve una instancia de PRAW autenticada."""
    return praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
    )

def fetch_hot_posts(subreddit, limit=10):
    """Obtiene las publicaciones 'hot' de un subreddit."""
    posts = []
    print(f"  -> Buscando publicaciones 'hot'...")
    try:
        for submission in subreddit.hot(limit=limit):
            posts.append({
                'id': submission.id,
                'subreddit': subreddit.display_name,
                'title': submission.title,
                'score': submission.score,
                'url': submission.url,
                'created_utc': datetime.datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'hot'
            })
    except Exception as e:
        print(f"    Error al obtener posts 'hot': {e}")
    return posts

def fetch_portfolio_posts(subreddit, assets, limit=25):
    """Busca publicaciones nuevas que mencionen activos del portafolio."""
    posts = []
    # Creamos una consulta de búsqueda que une los activos con "OR"
    query = ' OR '.join(f'"{asset}"' for asset in assets)
    print(f"  -> Buscando menciones recientes de activos del portafolio...")
    try:
        # Buscamos en el subreddit ordenando por 'new'
        for submission in subreddit.search(query, sort='new', limit=limit):
            posts.append({
                'id': submission.id,
                'subreddit': subreddit.display_name,
                'title': submission.title,
                'score': submission.score,
                'url': submission.url,
                'created_utc': datetime.datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'portfolio_mention'
            })
    except Exception as e:
        print(f"    Error al buscar menciones: {e}")
    return posts

def save_to_csv(posts, filename="reddit_financial_posts.csv"):
    """Guarda una lista de posts en un archivo CSV."""
    if not posts:
        print("No hay publicaciones para guardar.")
        return

    # Usamos un set para obtener las claves de forma dinámica del primer post
    headers = list(posts[0].keys())
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(posts)
    print(f"\n📁 Resultados guardados exitosamente en el archivo '{filename}'")


if __name__ == "__main__":
    reddit = initialize_reddit()
    all_posts = []
    seen_post_ids = set() # Para evitar duplicados

    print("Iniciando monitor de Reddit para subreddits financieros...")

    for sub_name in TARGET_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            print(f"\nRevisando r/{sub_name}...")
            
            # 1. Obtener publicaciones 'hot'
            hot_posts = fetch_hot_posts(subreddit)
            
            # 2. Obtener menciones a nuestro portafolio
            portfolio_posts = fetch_portfolio_posts(subreddit, PORTFOLIO_ASSETS)
            
            # Combinar y evitar duplicados
            for post in hot_posts + portfolio_posts:
                if post['id'] not in seen_post_ids:
                    all_posts.append(post)
                    seen_post_ids.add(post['id'])

        except Exception as e:
            print(f"No se pudo procesar r/{sub_name}: {e}")

    if all_posts:
        # Ordenar los resultados por fecha de creación, de más reciente a más antiguo
        all_posts.sort(key=lambda x: x['created_utc'], reverse=True)
        save_to_csv(all_posts)
    else:
        print("\nNo se encontraron publicaciones relevantes en esta ejecución.")

```

-----

### **Paso 4: Ejecución y Personalización**

1.  **Guarda el código** en el archivo `reddit_monitor.py`.
2.  **Abre una terminal o línea de comandos**, navega a la carpeta donde guardaste el archivo.
3.  **Ejecuta el script** con el comando: `python reddit_monitor.py`

Verás cómo el script empieza a buscar en cada subreddit. Al finalizar, creará un archivo llamado `reddit_financial_posts.csv` en la misma carpeta, listo para que lo abras con Excel, Google Sheets o lo analices con Pandas.

**Para personalizarlo:**

  * **Cambia tus credenciales:** Edita las variables `CLIENT_ID`, `CLIENT_SECRET` y `USER_AGENT`.
  * **Ajusta tu portafolio:** Modifica la lista `PORTFOLIO_ASSETS` para incluir los tickers y nombres de las empresas o criptomonedas que te interesan.
  * **Selecciona Subreddits:** Añade o quita nombres de la lista `TARGET_SUBREDDITS`.