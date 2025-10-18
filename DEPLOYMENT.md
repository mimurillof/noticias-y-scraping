# 🚀 Guía de Deployment

Esta guía cubre el deployment del Portfolio News Scraper en diferentes plataformas.

---

## 📋 **Pre-requisitos**

Antes de hacer deployment, asegúrate de tener:

1. ✅ Cuenta en Supabase con:
   - Base de datos configurada (tablas: users, portfolios, assets)
   - Storage bucket creado: `portfolio-files`
   - Service Role Key y Anon Key

2. ✅ Portfolios con assets en la base de datos

3. ✅ Variables de entorno configuradas

---

## 🌐 **Heroku**

### **Paso 1: Instalar Heroku CLI**

```bash
# Windows (Chocolatey)
choco install heroku-cli

# Mac
brew install heroku/brew/heroku

# Linux
curl https://cli-assets.heroku.com/install.sh | sh
```

### **Paso 2: Login en Heroku**

```bash
heroku login
```

### **Paso 3: Crear aplicación**

```bash
heroku create tu-portfolio-news-scraper
```

### **Paso 4: Configurar variables de entorno**

```bash
heroku config:set SUPABASE_URL=https://tu-proyecto.supabase.co
heroku config:set SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
heroku config:set SUPABASE_ANON_KEY=tu_anon_key
heroku config:set SUPABASE_BUCKET_NAME=portfolio-files
heroku config:set PARALLEL_EXECUTION=true
heroku config:set MAX_WORKERS=3
```

### **Paso 5: Deploy**

```bash
git push heroku main
```

### **Paso 6: Configurar Heroku Scheduler**

```bash
# Instalar addon
heroku addons:create scheduler:standard

# Abrir dashboard del scheduler
heroku addons:open scheduler
```

En el dashboard:
1. Click en "Add Job"
2. Command: `python orchestrator.py`
3. Frequency: `Every hour` o `Every 6 hours`
4. Save

### **Paso 7: Verificar logs**

```bash
heroku logs --tail
```

### **Paso 8: Ejecutar manualmente (opcional)**

```bash
heroku run python orchestrator.py
```

---

## ☁️ **AWS Lambda**

### **Paso 1: Preparar paquete de deployment**

```bash
# Crear directorio
mkdir lambda-package
cd lambda-package

# Instalar dependencias
pip install -r ../requirements.txt -t .

# Copiar código fuente
cp ../*.py .

# Crear ZIP
zip -r ../deployment-package.zip .
```

### **Paso 2: Crear función Lambda**

1. Ir a AWS Lambda Console
2. Click "Create function"
3. Configuración:
   - **Name**: portfolio-news-scraper
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64

### **Paso 3: Subir código**

```bash
aws lambda update-function-code \
  --function-name portfolio-news-scraper \
  --zip-file fileb://deployment-package.zip
```

### **Paso 4: Configurar función**

```bash
# Handler
aws lambda update-function-configuration \
  --function-name portfolio-news-scraper \
  --handler orchestrator.lambda_handler \
  --timeout 300 \
  --memory-size 512

# Variables de entorno
aws lambda update-function-configuration \
  --function-name portfolio-news-scraper \
  --environment Variables="{
    SUPABASE_URL=https://tu-proyecto.supabase.co,
    SUPABASE_SERVICE_ROLE_KEY=tu_key,
    SUPABASE_ANON_KEY=tu_key,
    SUPABASE_BUCKET_NAME=portfolio-files
  }"
```

### **Paso 5: Crear trigger con EventBridge**

1. Ir a EventBridge Console
2. Create rule:
   - **Name**: portfolio-news-schedule
   - **Schedule expression**: `rate(1 hour)` o `cron(0 */6 * * ? *)`
3. Target: Lambda function → portfolio-news-scraper

### **Paso 6: Test**

```bash
aws lambda invoke \
  --function-name portfolio-news-scraper \
  --payload '{}' \
  response.json

cat response.json
```

---

## 🐳 **Docker**

### **Paso 1: Crear Dockerfile**

Ya está incluido en el repositorio. Contenido:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY *.py .

# Comando por defecto
CMD ["python", "orchestrator.py"]
```

### **Paso 2: Build**

```bash
docker build -t portfolio-news-scraper .
```

### **Paso 3: Run local**

```bash
docker run --env-file .env portfolio-news-scraper
```

### **Paso 4: Deploy a Docker Hub**

```bash
# Tag
docker tag portfolio-news-scraper tu-usuario/portfolio-news-scraper:latest

# Push
docker push tu-usuario/portfolio-news-scraper:latest
```

### **Paso 5: Deploy a producción**

**AWS ECS:**
```bash
# Crear task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Crear servicio
aws ecs create-service \
  --cluster portfolio-cluster \
  --service-name portfolio-news \
  --task-definition portfolio-news-scraper \
  --desired-count 1
```

**Google Cloud Run:**
```bash
# Deploy
gcloud run deploy portfolio-news-scraper \
  --image gcr.io/tu-proyecto/portfolio-news-scraper \
  --platform managed \
  --region us-central1 \
  --set-env-vars SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...
```

---

## ⏰ **Cron Jobs (Linux)**

### **Paso 1: Clonar repositorio en servidor**

```bash
cd /opt
git clone https://github.com/mimurillof/noticias-y-scraping.git
cd noticias-y-scraping
```

### **Paso 2: Configurar environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **Paso 3: Crear script wrapper**

```bash
cat > /opt/noticias-y-scraping/run.sh << 'EOF'
#!/bin/bash
cd /opt/noticias-y-scraping
source .venv/bin/activate
python orchestrator.py
EOF

chmod +x /opt/noticias-y-scraping/run.sh
```

### **Paso 4: Configurar cron**

```bash
crontab -e
```

Agregar línea:

```cron
# Cada hora
0 * * * * /opt/noticias-y-scraping/run.sh >> /var/log/portfolio-news.log 2>&1

# Cada 6 horas
0 */6 * * * /opt/noticias-y-scraping/run.sh >> /var/log/portfolio-news.log 2>&1

# Cada día a las 8am
0 8 * * * /opt/noticias-y-scraping/run.sh >> /var/log/portfolio-news.log 2>&1
```

---

## 🔒 **Seguridad en Producción**

### **Variables de Entorno**

✅ **HACER:**
- Usar variables de entorno para credenciales
- Rotar keys regularmente
- Usar Service Role Key solo en backend

❌ **NO HACER:**
- Commitear `.env` al repositorio
- Hardcodear credenciales en código
- Compartir keys públicamente

### **Supabase RLS Policies**

```sql
-- Permitir que usuarios lean solo sus portfolios
CREATE POLICY "Users can read own portfolios"
ON portfolios FOR SELECT
USING (auth.uid() = user_id);

-- Permitir que usuarios lean solo sus archivos
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'portfolio-files' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Permitir que el backend escriba archivos
CREATE POLICY "Backend can write files"
ON storage.objects FOR INSERT
USING (bucket_id = 'portfolio-files');
```

---

## 📊 **Monitoring**

### **Logs**

**Heroku:**
```bash
heroku logs --tail --app tu-app
```

**AWS Lambda:**
```bash
aws logs tail /aws/lambda/portfolio-news-scraper --follow
```

**Docker:**
```bash
docker logs -f container-id
```

### **Alertas**

**Sentry (Recomendado):**

```bash
pip install sentry-sdk
```

Agregar a `orchestrator.py`:

```python
import sentry_sdk

sentry_sdk.init(
    dsn="tu-sentry-dsn",
    traces_sample_rate=1.0
)
```

**Healthchecks.io:**

```python
import requests

HEALTHCHECK_URL = "https://hc-ping.com/tu-uuid"

try:
    # Ejecutar orchestrator
    run_orchestrator()
    requests.get(HEALTHCHECK_URL)  # Success
except Exception as e:
    requests.get(f"{HEALTHCHECK_URL}/fail")  # Failure
```

---

## 🧪 **Testing Pre-Deployment**

Antes de hacer deployment, ejecuta estos tests:

### **1. Test de conexión a Supabase**

```bash
python -c "from supabase_client import get_supabase_client; client = get_supabase_client(); print('✅ Supabase conectado')"
```

### **2. Test de carga de portfolios**

```bash
python -c "from portfolio_service import PortfolioService; service = PortfolioService(); users = service.get_all_users_with_portfolios(); print(f'✅ {len(users)} usuarios cargados')"
```

### **3. Test completo**

```bash
FILTER_PORTFOLIO_ID=1 PARALLEL_EXECUTION=false python orchestrator.py
```

---

## 📈 **Escalabilidad**

### **Optimización para muchos portfolios**

Si tienes **100+ portfolios**, considera:

1. **Ejecución paralela:**
```bash
PARALLEL_EXECUTION=true MAX_WORKERS=10 python orchestrator.py
```

2. **Dividir por batches:**
```bash
# Batch 1: Portfolios 1-50
FILTER_PORTFOLIO_ID=1-50 python orchestrator.py

# Batch 2: Portfolios 51-100
FILTER_PORTFOLIO_ID=51-100 python orchestrator.py
```

3. **Usar queue (Celery + Redis):**
```python
# Agregar cada portfolio a una cola
for portfolio in portfolios:
    process_portfolio.delay(portfolio.id)
```

---

## 🔄 **CI/CD**

### **GitHub Actions**

Crear `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to Heroku
        uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{secrets.HEROKU_API_KEY}}
          heroku_app_name: "tu-app"
          heroku_email: "tu-email@example.com"
```

---

## 🆘 **Troubleshooting**

### **Error: Module not found**
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

### **Error: Timeout**
```bash
# Aumentar timeout (Lambda)
aws lambda update-function-configuration \
  --function-name portfolio-news-scraper \
  --timeout 600
```

### **Error: Out of memory**
```bash
# Aumentar memoria (Lambda)
aws lambda update-function-configuration \
  --function-name portfolio-news-scraper \
  --memory-size 1024
```

---

**Última actualización:** 18 de octubre de 2025
