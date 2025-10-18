# 🚀 Quick Reference - Portfolio News Scraper

Este es un documento de referencia rápida para desarrollo y deployment.

---

## 📦 **Archivos Esenciales**

### **Core Python (8 archivos):**
- `orchestrator.py` - Punto de entrada, orquestación multi-cliente
- `portfolio_service.py` - Lógica de negocio, modelos de datos
- `supabase_client.py` - Cliente Supabase (Singleton pattern)
- `symbol_normalizer.py` - Normalización de 50+ símbolos
- `Script_noticias.py` - Scraper de noticias (yfinance)
- `scrape_sentiment.py` - Fear & Greed Index
- `tradingview_scraper.py` - Ideas de TradingView
- `main.py` - Wrapper legacy (usa orchestrator)

### **Configuración (6 archivos):**
- `Dockerfile` - Container optimizado
- `docker-compose.yml` - Testing local
- `.dockerignore` - Exclusiones para Docker
- `Procfile` - Deployment (Heroku, etc.)
- `.env.example` - Template de variables
- `.gitignore` - Git exclusions

### **Documentación (4 archivos):**
- `README.md` - Documentación principal (600+ líneas)
- `DEPLOYMENT.md` - Guía de deployment completa
- `CHANGELOG.md` - Historial de versiones
- `LICENSE` - MIT License

### **Utilidades (2 archivos):**
- `verify_deployment.py` - Script de verificación pre-deployment
- `requirements.txt` - Dependencias Python

---

## ⚡ **Comandos Rápidos**

### **Setup Local:**
```bash
# Clonar y setup
git clone https://github.com/mimurillof/noticias-y-scraping.git
cd noticias-y-scraping
python -m venv .venv
.venv\Scripts\activate  # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# Configurar
cp .env.example .env
# Editar .env con credenciales

# Verificar
python verify_deployment.py

# Ejecutar
python orchestrator.py
```

### **Testing:**
```bash
# Un solo portfolio
set FILTER_PORTFOLIO_ID=1
python orchestrator.py

# Modo secuencial
set PARALLEL_EXECUTION=false
python orchestrator.py

# Modo paralelo
set PARALLEL_EXECUTION=true
set MAX_WORKERS=3
python orchestrator.py
```

### **Docker:**
```bash
# Build
docker build -t portfolio-news-scraper .

# Run local
docker run --env-file .env portfolio-news-scraper

# Con compose
docker-compose up

# Push a registry
docker tag portfolio-news-scraper tu-usuario/portfolio-news-scraper
docker push tu-usuario/portfolio-news-scraper
```

### **Heroku:**
```bash
# Setup
heroku create portfolio-news-scraper
heroku config:set SUPABASE_URL=...
heroku config:set SUPABASE_SERVICE_ROLE_KEY=...

# Deploy
git push heroku main

# Scheduler
heroku addons:create scheduler:standard
heroku addons:open scheduler
# Add job: python orchestrator.py (hourly)

# Logs
heroku logs --tail
```

### **AWS Lambda:**
```bash
# Package
pip install -r requirements.txt -t ./package
cp *.py ./package/
cd package && zip -r ../deployment-package.zip .

# Deploy
aws lambda create-function \
  --function-name portfolio-news-scraper \
  --runtime python3.9 \
  --handler orchestrator.lambda_handler \
  --zip-file fileb://deployment-package.zip \
  --role arn:aws:iam::ACCOUNT:role/lambda-role

# Configure
aws lambda update-function-configuration \
  --function-name portfolio-news-scraper \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...}"

# Schedule (EventBridge)
# Create rule with schedule: rate(1 hour)
```

---

## 🔐 **Variables de Entorno**

### **Requeridas:**
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### **Opcionales:**
```bash
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_BUCKET_NAME=portfolio-files  # default
FILTER_PORTFOLIO_ID=1  # test un solo portfolio
PARALLEL_EXECUTION=true  # default: false
MAX_WORKERS=3  # default: 3
```

---

## 📊 **Formato de Output**

**Archivo:** `{user_id}/portfolio_news.json` en Supabase Storage

```json
{
  "sentiment": {
    "value": 65,
    "classification": "Greed",
    "timestamp": "2025-01-18T10:30:00Z"
  },
  "news": [
    {
      "title": "Bitcoin Reaches New High",
      "url": "https://...",
      "source": "Bloomberg",
      "published_utc": "2025-01-18T10:00:00Z",
      "tickers": ["BTC-USD"]
    }
  ],
  "tradingview_ideas": [
    {
      "title": "BTC/USD Long Setup",
      "url": "https://...",
      "author": "trader123",
      "published": "2 hours ago",
      "symbol": "BTCUSD"
    }
  ]
}
```

---

## 🔧 **Normalización de Símbolos**

**Cryptos:**
- BTCUSD → BTC-USD
- ETHUSD → ETH-USD
- SOLUSD → SOL-USD

**Stablecoins:**
- USDTUSD → USDT-USD
- PAXGUSD → PAXG-USD

**Acciones:**
- NVD / NVD.F → NVDA
- MSFT.F → MSFT
- GOOG.F → GOOGL

**Ver `symbol_normalizer.py` para la lista completa (50+ símbolos)**

---

## 🐛 **Troubleshooting Rápido**

### **Error: Module not found**
```bash
pip install -r requirements.txt --force-reinstall
```

### **Error: No se encontraron portfolios**
- Verificar que existan portfolios en Supabase
- Verificar las credenciales (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

### **Error: 0 noticias obtenidas**
- Verificar que los símbolos estén correctos en la tabla `assets`
- Verificar que yfinance no esté bloqueado (rate limit)
- Usar `symbol_normalizer.py` para normalizar símbolos

### **Error: Supabase connection failed**
- Verificar variables de entorno
- Verificar conectividad de red
- Verificar que el Service Role Key tenga permisos

---

## 📈 **Performance Reference**

| Escenario | Tiempo |
|-----------|--------|
| 1 portfolio | ~5-10s |
| 5 portfolios (secuencial) | ~25-50s |
| 5 portfolios (paralelo, 3 workers) | ~10-15s |

**Optimizaciones:**
- Usar `PARALLEL_EXECUTION=true` para múltiples portfolios
- Ajustar `MAX_WORKERS` según CPU disponible
- Considerar Celery + Redis para > 20 portfolios

---

## 📚 **Recursos**

- **Documentación completa:** [README.md](README.md)
- **Guía de deployment:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Historial de cambios:** [CHANGELOG.md](CHANGELOG.md)
- **Repositorio:** https://github.com/mimurillof/noticias-y-scraping
- **Issues:** https://github.com/mimurillof/noticias-y-scraping/issues

---

## 🎯 **Checklist Pre-Deployment**

- [ ] Variables de entorno configuradas
- [ ] `python verify_deployment.py` pasa todos los tests
- [ ] Test local exitoso: `python orchestrator.py`
- [ ] Portfolios con assets en Supabase
- [ ] Storage bucket `portfolio-files` creado
- [ ] RLS policies configuradas
- [ ] `.env` en `.gitignore` (no commitear)
- [ ] Dependencies actualizadas: `pip list --outdated`

---

**Última actualización:** 18 de enero de 2025  
**Versión:** 1.0.0  
**Autor:** Miguel Murillo ([@mimurillof](https://github.com/mimurillof))
