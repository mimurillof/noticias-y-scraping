# 📊 Portfolio News Scraper - Multi-Client System

Sistema automatizado para recopilar noticias financieras, análisis de sentimiento del mercado e ideas de TradingView para múltiples portfolios de clientes almacenados en Supabase.

---

## 🚀 **Quick Start**

```bash
# 1. Clonar repositorio
git clone https://github.com/mimurillof/noticias-y-scraping.git
cd noticias-y-scraping

# 2. Configurar environment
python -m venv .venv
.venv\Scripts\activate  # Linux/Mac: source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Supabase

# 5. Verificar configuración
python verify_deployment.py

# 6. Ejecutar
python orchestrator.py
```

**📖 Ver [DEPLOYMENT.md](DEPLOYMENT.md) para deployment en producción (Heroku, AWS, Docker)**

---

## 🎯 **Características**

- ✅ **Multi-cliente**: Procesa portfolios de múltiples usuarios desde Supabase
- ✅ **Noticias financieras**: Obtiene noticias de yfinance con normalización de símbolos
- ✅ **Sentimiento del mercado**: Fear & Greed Index en tiempo real
- ✅ **Ideas de TradingView**: Análisis técnico de la comunidad
- ✅ **Almacenamiento en cloud**: Guarda resultados en Supabase Storage
- ✅ **Ejecución paralela/secuencial**: Optimizado para performance
- ✅ **Normalización de símbolos**: Soporta cryptos, acciones, stablecoins

---

## 📁 **Estructura del Proyecto**

```
noticias-y-scraping/
├── orchestrator.py              # 🎯 Punto de entrada principal
├── portfolio_service.py         # 📊 Lógica de negocio y modelos
├── supabase_client.py          # 🗄️  Cliente de Supabase (Singleton)
├── symbol_normalizer.py        # 🔧 Normalización de símbolos
├── Script_noticias.py          # 📰 Scraper de noticias (yfinance)
├── scrape_sentiment.py         # 😨 Fear & Greed Index
├── tradingview_scraper.py      # 📈 Ideas de TradingView
├── requirements.txt            # 📦 Dependencias Python
├── Procfile                    # 🚀 Configuración de deployment
├── .env                        # 🔐 Variables de entorno
└── README.md                   # 📖 Este archivo
```

---

## 🗄️ **Esquema de Base de Datos (Supabase)**

### **Tabla: `users`**
```sql
id (uuid, PK)
email (text)
created_at (timestamp)
```

### **Tabla: `portfolios`**
```sql
id (integer, PK)
user_id (uuid, FK → users.id)
portfolio_name (text)
description (text)
created_at (timestamp)
```

### **Tabla: `assets`**
```sql
id (integer, PK)
portfolio_id (integer, FK → portfolios.id)
asset_symbol (text)          -- Ejemplo: AAPL, BTC-USD, NVDA
quantity (numeric)
created_at (timestamp)
```

### **Storage Bucket: `portfolio-files`**
```
Estructura:
portfolio-files/
└── {user_id}/
    └── portfolio_news.json
```

---

## 🚀 **Instalación**

### **1. Clonar el repositorio**
```bash
git clone https://github.com/mimurillof/noticias-y-scraping.git
cd noticias-y-scraping
```

### **2. Crear entorno virtual**
```bash
python -m venv .venv
```

**Windows:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### **3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

### **4. Configurar variables de entorno**

Crea un archivo `.env` en la raíz del proyecto:

```env
# Supabase Configuration
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
SUPABASE_ANON_KEY=tu_anon_key

# Storage Configuration
SUPABASE_BUCKET_NAME=portfolio-files

# Execution Configuration (opcional)
FILTER_PORTFOLIO_ID=          # Dejar vacío para procesar todos
PARALLEL_EXECUTION=true       # true = paralelo, false = secuencial
MAX_WORKERS=3                 # Número de workers para ejecución paralela
```

---

## ⚙️ **Uso**

### **Ejecución Básica**

```bash
python orchestrator.py
```

### **Procesar un Portfolio Específico**

```bash
# Windows PowerShell
$env:FILTER_PORTFOLIO_ID="1"
python orchestrator.py

# Linux/Mac
export FILTER_PORTFOLIO_ID=1
python orchestrator.py
```

### **Modo de Ejecución**

```bash
# Paralelo (por defecto)
$env:PARALLEL_EXECUTION="true"
python orchestrator.py

# Secuencial (recomendado para debugging)
$env:PARALLEL_EXECUTION="false"
python orchestrator.py
```

---

## 🔄 **Flujo de Ejecución**

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR START                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  1. CARGAR USUARIOS Y PORTFOLIOS DESDE SUPABASE             │
│     • Consulta tabla 'users'                                 │
│     • Consulta tabla 'portfolios' (JOIN con users)          │
│     • Consulta tabla 'assets' (JOIN con portfolios)         │
│     • Filtra por FILTER_PORTFOLIO_ID (si está configurado)  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  2. NORMALIZACIÓN DE SÍMBOLOS (symbol_normalizer.py)       │
│     • BTCUSD    → BTC-USD   (crypto)                        │
│     • PAXGUSD   → PAXG-USD  (stablecoin)                    │
│     • NVD       → NVDA      (ticker incompleto)             │
│     • NVD.F     → NVDA      (exchange alemán)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  3. PROCESAMIENTO POR PORTFOLIO                             │
│     ┌─────────────────────────────────────────────────┐    │
│     │  PARALELO (ThreadPoolExecutor)                  │    │
│     │  • Procesa múltiples portfolios simultáneamente │    │
│     │  • MAX_WORKERS = 3 (por defecto)                │    │
│     └─────────────────────────────────────────────────┘    │
│               O                                              │
│     ┌─────────────────────────────────────────────────┐    │
│     │  SECUENCIAL                                      │    │
│     │  • Procesa un portfolio a la vez                │    │
│     │  • Mejor para debugging                         │    │
│     └─────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  4. PARA CADA PORTFOLIO: EJECUTAR 3 TAREAS                  │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  TAREA 1: Sentimiento del Mercado                  │    │
│  │  (scrape_sentiment.py)                             │    │
│  │  • Consulta CNN Fear & Greed Index                 │    │
│  │  • Retorna: {value: 0-100, description: str}       │    │
│  │  • Tiempo: ~1-2 segundos                           │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  TAREA 2: Noticias del Portfolio                   │    │
│  │  (Script_noticias.py)                              │    │
│  │  • Para cada símbolo normalizado:                  │    │
│  │    - Consulta yfinance API                         │    │
│  │    - Obtiene noticias (últimas 24 horas)           │    │
│  │    - Formatea: title, subtitle, source, url, etc.  │    │
│  │  • Filtra duplicados (por UUID)                    │    │
│  │  • Limita a 3 noticias por símbolo                 │    │
│  │  • Tiempo: ~2-4 segundos                           │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  TAREA 3: Ideas de TradingView                     │    │
│  │  (tradingview_scraper.py)                          │    │
│  │  • Scraping de ideas recientes                     │    │
│  │  • Categorías: stock, crypto, market               │    │
│  │  • Información: title, author, url, image          │    │
│  │  • Limita a 5 ideas por portfolio                  │    │
│  │  • Tiempo: ~1-3 segundos                           │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  5. CONSTRUIR JSON DEL PORTFOLIO                            │
│     {                                                        │
│       "generated_at": "2025-10-18T...",                     │
│       "portfolio_id": 1,                                     │
│       "portfolio_name": "Mi Portfolio",                     │
│       "user_id": "uuid...",                                 │
│       "market_sentiment": {                                 │
│         "value": 27,                                        │
│         "description": "Fear"                               │
│       },                                                     │
│       "portfolio_news": [...],  // 3-9 noticias            │
│       "tradingview_ideas": [...] // 5 ideas                │
│     }                                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  6. SUBIR A SUPABASE STORAGE                                │
│     • Bucket: portfolio-files                               │
│     • Path: {user_id}/portfolio_news.json                   │
│     • Operación: Sobrescribe archivo existente              │
│     • Tiempo: ~1 segundo                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  7. GENERAR RESUMEN DE EJECUCIÓN                            │
│     • Total portfolios procesados                           │
│     • Exitosos / Fallidos                                   │
│     • Duración total                                        │
│     • Tasa de éxito                                         │
│     • Guarda en: orchestration_summary.json                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR END                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 **Formato de Salida (JSON)**

```json
{
  "generated_at": "2025-10-18T02:51:45.339207+00:00",
  "portfolio_id": 1,
  "portfolio_name": "Mi Portfolio",
  "user_id": "238ff453-ab78-42de-9b54-a63980ff56e3",
  "market_sentiment": {
    "value": 27,
    "description": "Fear"
  },
  "portfolio_news": [
    {
      "uuid": "9cbb5313-2786-395c-9ede-54e4bd17f7ce",
      "title": "Tesla, Nvidia, Rigetti, Praxis: Trending Stocks",
      "subtitle": "Tesla (TSLA) continued its slide...",
      "summary": "Tesla (TSLA) continued its slide in the pre-market...",
      "source": "Yahoo Finance Video",
      "url": "https://finance.yahoo.com/video/...",
      "published_at": "2025-10-17T12:49:25+00:00",
      "image": "https://s.yimg.com/...",
      "type": "VIDEO"
    }
  ],
  "tradingview_ideas": [
    {
      "id": "MPotC8EJ",
      "ticker": "TSLA",
      "category": "stock",
      "title": "Análisis Técnico de Tesla (TSLA)",
      "author": "por EA_GOLD_MAN_COPY_TRADE",
      "rating": null,
      "published_at": "2025-10-17T19:51:08+00:00",
      "idea_url": "https://es.tradingview.com/chart/TSLA/MPotC8EJ/",
      "image_url": "https://s3.tradingview.com/...",
      "source_url": "https://es.tradingview.com/symbols/NASDAQ-TSLA/ideas/"
    }
  ]
}
```

---

## 🔧 **Normalización de Símbolos**

El sistema normaliza automáticamente símbolos incorrectos o inconsistentes:

### **Cryptocurrencias**
```
BTCUSD   → BTC-USD
ETHUSD   → ETH-USD
SOLUSD   → SOL-USD
DOGEUSD  → DOGE-USD
```

### **Stablecoins**
```
PAXGUSD  → PAXG-USD
USDTUSD  → USDT-USD
USDCUSD  → USDC-USD
```

### **Tickers Incompletos**
```
NVD      → NVDA (NVIDIA)
APPL     → AAPL (Apple)
GOOG     → GOOGL (Google)
```

### **Exchanges Extranjeros**
```
NVD.F    → NVDA (Frankfurt → US)
AAPL.DE  → AAPL (Deutsche Börse → US)
```

**50+ símbolos soportados.** Ver `symbol_normalizer.py` para la lista completa.

---

## 🚀 **Deployment**

Para instrucciones **completas y detalladas** de deployment en múltiples plataformas, consulta:

### 👉 **[DEPLOYMENT.md](DEPLOYMENT.md)** 👈

El archivo `DEPLOYMENT.md` incluye:
- ✅ Heroku (con Heroku Scheduler)
- ✅ AWS Lambda (con EventBridge)
- ✅ Docker (standalone + compose)
- ✅ Cron Jobs (Linux)
- ✅ CI/CD (GitHub Actions)
- ✅ Monitoring y alertas
- ✅ Seguridad y best practices

### **Quick Deploy - Heroku**

```bash
# 1. Crear app
heroku create portfolio-news-scraper

# 2. Configurar variables de entorno
heroku config:set SUPABASE_URL=https://...
heroku config:set SUPABASE_SERVICE_ROLE_KEY=...

# 3. Deploy
git push heroku main

# 4. Configurar scheduler
heroku addons:create scheduler:standard
# Add job: python orchestrator.py (hourly)
```

### **Quick Deploy - Docker**

```bash
# Build y run
docker build -t portfolio-news-scraper .
docker run --env-file .env portfolio-news-scraper

# O con docker-compose
docker-compose up
```

### **Quick Deploy - AWS Lambda**

```bash
# Empaquetar y subir
pip install -r requirements.txt -t ./package
cp *.py ./package/
cd package && zip -r ../deployment-package.zip .

# Crear función
aws lambda create-function \
  --function-name portfolio-news-scraper \
  --runtime python3.9 \
  --handler orchestrator.lambda_handler \
  --zip-file fileb://deployment-package.zip
```

**Ver instrucciones completas en [DEPLOYMENT.md](DEPLOYMENT.md)**

---

## 📈 **Performance**

### **Tiempos de Ejecución (por portfolio)**

| Tarea | Tiempo Promedio |
|-------|-----------------|
| Sentimiento del mercado | 1-2 segundos |
| Noticias (3 símbolos) | 2-4 segundos |
| Ideas de TradingView | 1-3 segundos |
| Upload a Supabase | 1 segundo |
| **Total** | **5-10 segundos** |

### **Ejecución Paralela vs Secuencial**

**3 portfolios:**
- **Paralelo**: ~10-15 segundos (3 workers)
- **Secuencial**: ~20-30 segundos

**10 portfolios:**
- **Paralelo**: ~35-50 segundos (3 workers)
- **Secuencial**: ~60-100 segundos

---

## 🐛 **Troubleshooting**

### **Error: "No se encontraron portfolios"**
- Verifica que existan portfolios en Supabase
- Verifica que los portfolios tengan assets asociados
- Revisa `FILTER_PORTFOLIO_ID` si está configurado

### **Error: "0 noticias obtenidas"**
- Verifica que los símbolos estén correctos en la tabla `assets`
- Revisa si yfinance está disponible (puede haber rate limiting)
- Verifica la conexión a internet

### **Error: "Supabase connection failed"**
- Verifica las variables de entorno (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
- Verifica que el bucket `portfolio-files` exista
- Verifica permisos de storage en Supabase

### **Símbolos no se normalizan**
- Verifica que `symbol_normalizer.py` esté importado correctamente
- Revisa logs para ver mensajes de normalización (`🔧 Normalizado: ...`)
- Si el símbolo no está en el diccionario, agrégalo manualmente

---

## 🔒 **Seguridad**

### **Variables de Entorno**
- ⚠️ **NUNCA** commitees el archivo `.env` al repositorio
- Usa `SUPABASE_SERVICE_ROLE_KEY` solo en backend (servidor)
- Usa `SUPABASE_ANON_KEY` para operaciones de solo lectura

### **Supabase Row Level Security (RLS)**
```sql
-- Ejemplo de política para users
CREATE POLICY "Users can read own portfolios"
ON portfolios FOR SELECT
USING (auth.uid() = user_id);

-- Ejemplo de política para storage
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
USING (bucket_id = 'portfolio-files' AND auth.uid()::text = (storage.foldername(name))[1]);
```

---

## 📦 **Dependencias Principales**

```
supabase==2.4.0          # Cliente de Supabase
yfinance==0.2.48         # API de noticias financieras
beautifulsoup4==4.12.3   # Web scraping
requests==2.31.0         # HTTP requests
python-dotenv==1.0.1     # Variables de entorno
```

Ver `requirements.txt` para la lista completa.

---

## 🤝 **Contribuir**

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 **Licencia**

Este proyecto está bajo la licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👤 **Autor**

**Miguel Murillo**
- GitHub: [@mimurillof](https://github.com/mimurillof)
- Repositorio: [noticias-y-scraping](https://github.com/mimurillof/noticias-y-scraping)

---

## 🎯 **Roadmap**

- [ ] Soporte para más fuentes de noticias (Bloomberg, Reuters)
- [ ] Dashboard web para visualización
- [ ] Notificaciones por email/Slack
- [ ] Análisis de sentimiento con NLP
- [ ] Detección de tendencias y alertas
- [ ] API REST para consultar resultados
- [ ] Soporte para más exchanges (Binance, Coinbase)

---

**Última actualización:** 18 de octubre de 2025
