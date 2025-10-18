# Changelog

Todos los cambios notables a este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.0.0] - 2025-01-18

### 🎉 **Lanzamiento Inicial - Sistema Multi-Cliente de Noticias de Portfolio**

#### ✅ Agregado

**Core Features:**
- ✨ Sistema de orquestación multi-cliente para procesar múltiples portfolios
- 📰 Scraping de noticias financieras desde yfinance API
- 😨 Análisis de sentimiento del mercado (Fear & Greed Index)
- 📈 Scraping de ideas de TradingView
- 🗄️ Integración completa con Supabase (PostgreSQL + Storage)
- 🔧 Normalización automática de 50+ símbolos de trading
- ⚡ Soporte para ejecución paralela y secuencial
- 📊 Modelos de datos tipados con dataclasses

**Infrastructure:**
- 🐳 Dockerfile optimizado para deployment en containers
- 🚀 Procfile configurado para Heroku y plataformas similares
- 📝 docker-compose.yml para testing local
- 🔐 Variables de entorno para configuración segura
- 🧪 Script de verificación pre-deployment

**Documentation:**
- 📖 README.md completo (600+ líneas) con:
  - Arquitectura del sistema
  - Diagrama de flujo ASCII
  - Ejemplos de uso
  - Formato de salida JSON
  - Tabla de normalización de símbolos
- 🚀 DEPLOYMENT.md detallado con instrucciones para:
  - Heroku (con Heroku Scheduler)
  - AWS Lambda (con EventBridge)
  - Docker (standalone + compose)
  - Cron Jobs (Linux)
  - CI/CD (GitHub Actions)
  - Monitoring y seguridad
- 📝 CHANGELOG.md (este archivo)
- 🔐 .env.example con todas las variables requeridas
- ⚖️ LICENSE (MIT)

**Code Quality:**
- 🎯 Type hints completos en todo el código
- 📝 Docstrings detallados en funciones críticas
- 🧹 Código limpio y modular (8 archivos core)
- 🔒 Patrón Singleton para conexión a Supabase
- ⚡ Optimizaciones de performance (batching, caching)

#### 🐛 Corregido

- 🔧 **yfinance API structure change**: Adaptado a la nueva estructura `{id, content: {...}}`
  - Antes: `{uuid, title, publisher, link, providerPublishTime, ...}`
  - Ahora: `{id, content: {title, pubDate, provider: {displayName}, clickThroughUrl: {url}, ...}}`
- ⏰ **Time filter bug**: Filtro de tiempo aumentado de 30 minutos a 24 horas para capturar más noticias
- 🔄 **Normalization loop bug**: Corregido uso de `tickers` en lugar de `normalized_tickers`
- 📊 **Portfolio fetching**: Sistema ahora obtiene correctamente 24+ noticias, filtra ~18 válidas, retorna 3 top

#### 🗑️ Eliminado

**Limpieza del repositorio (27 archivos eliminados):**

- **Debug/Test Scripts (11):**
  - debug_time_filter.py
  - debug_yfinance.py
  - download_portfolio_json.py
  - inspect_news_structure.py
  - test_news_formatting.py
  - test_system.py
  - update_assets_for_testing.py
  - validate_deployment.py
  - migration_helper.py
  - main_legacy_backup.py
  - tmp_tv.py

- **Documentación Redundante (11):**
  - EXECUTE_NOW.md
  - FIXES_APPLIED.md
  - FLOW_DIAGRAM.txt
  - IMPLEMENTATION_SUMMARY.md
  - MIGRATION_FROM_MAIN.md
  - NORMALIZATION_SUMMARY.md
  - QUICKSTART.md
  - README_MULTI_CLIENT.md
  - STORAGE_CHANGES.md
  - SYMBOL_NORMALIZATION.md
  - COMMANDS.ps1

- **Archivos Temporales (5):**
  - debug_output.html
  - pagina.html
  - portfolio_news.json
  - orchestration_summary.json
  - __pycache__/

#### 📦 Dependencias

```
supabase>=2.0.0        # Cliente oficial de Supabase
yfinance>=0.2.48       # Yahoo Finance API
beautifulsoup4>=4.11.1 # HTML parsing
requests>=2.28.1       # HTTP requests
python-dotenv>=0.21.0  # Variables de entorno
```

#### 🎯 Características Técnicas

**Normalización de Símbolos:**
- 🪙 Cryptos: BTCUSD → BTC-USD, ETHUSD → ETH-USD
- 💵 Stablecoins: USDTUSD → USDT-USD, PAXGUSD → PAXG-USD
- 📊 Acciones: NVD → NVDA, MSFT.F → MSFT
- 🌍 Foreign exchanges: *.F → US ticker

**Performance:**
- ⚡ Portfolio individual: ~5-10 segundos
- ⚡ 5 portfolios secuencial: ~25-50 segundos
- ⚡ 5 portfolios paralelo (3 workers): ~10-15 segundos

**Storage:**
- 📁 Formato: `{user_id}/portfolio_news.json`
- 🗄️ Bucket: `portfolio-files` (Supabase Storage)
- 🔒 RLS: Solo el usuario puede leer sus archivos
- 📝 Estructura JSON: `{sentiment, news[], tradingview_ideas[]}`

#### 🔐 Seguridad

- ✅ Variables de entorno para credenciales
- ✅ Service Role Key solo en backend
- ✅ .gitignore configurado (excludes .env, __pycache__, *.log)
- ✅ .dockerignore optimizado
- ✅ RLS policies en Supabase
- ✅ Usuario no-root en Dockerfile

#### 🧪 Testing

- ✅ Script de verificación pre-deployment (`verify_deployment.py`)
- ✅ Checks: Variables, Dependencias, Archivos Core, Conexión Supabase, Datos de Portfolio
- ✅ Validación de imports y configuración

---

## [Unreleased]

### 🚧 Planeado

- [ ] Rate limiting para APIs externas
- [ ] Retry con exponential backoff
- [ ] Celery + Redis para queue management
- [ ] Métricas de Prometheus
- [ ] Tests unitarios con pytest
- [ ] GitHub Actions CI/CD
- [ ] API REST para consultar resultados
- [ ] WebSocket para notificaciones en tiempo real
- [ ] Dashboard de monitoring

---

**Convenciones del Changelog:**

- **Agregado**: Nuevas características
- **Cambiado**: Cambios en funcionalidad existente
- **Deprecado**: Características que serán eliminadas
- **Eliminado**: Características eliminadas
- **Corregido**: Bugs corregidos
- **Seguridad**: Vulnerabilidades corregidas
