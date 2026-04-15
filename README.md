# Section 8 MLS Auto-Search — Miami-Dade

Herramienta para realtors que automatiza la búsqueda de propiedades en el MLS de Miami-Dade que califican para el programa de Sección 8 (Housing Choice Voucher), filtrando por Payment Standards 2024 de HUD.

---

## Qué hace

- Conecta con la **Spark API de MIAMI MLS** cada hora de forma automática
- Filtra listings por **Payment Standards 2024** de Miami-Dade (por ZIP y número de habitaciones)
- Calcula un **Opportunity Score** (0–100) por propiedad basado en precio, historial de aceptación, demanda de la zona y más
- Presenta los resultados en un **dashboard web** con filtros interactivos
- Todos los criterios se configuran en un solo archivo (`config.py`) sin tocar el código

---

## Estructura del repositorio

```
section8-mls-miami/
├── scripts/
│   └── scraper.py            # Motor de búsqueda y filtrado
├── dashboard/
│   └── index.html            # Dashboard web (abre en navegador)
├── data/
│   └── payment_standards_2024.json   # FMR HUD por ZIP y bedrooms
├── config.py                 # Todos los filtros y parámetros
├── requirements.txt
├── .env.template             # Plantilla de credenciales
├── .gitignore
└── README.md
```

---

## Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/tu-usuario/section8-mls-miami.git
cd section8-mls-miami
```

### 2. Instala dependencias

```bash
pip install -r requirements.txt
```

### 3. Configura credenciales

```bash
cp .env.template .env
```

Edita `.env` con tus credenciales de la Spark API:

```
SPARK_CLIENT_ID=tu_client_id
SPARK_CLIENT_SECRET=tu_client_secret
```

> Para obtener acceso a la Spark API: entra a **mmls.com → Member Services → API Access** o llama al (305) 468-7000.

### 4. Ajusta los filtros (opcional)

Edita `config.py` para personalizar:

```python
MAX_RENT       = 3500     # Precio máximo a buscar
MIN_BEDROOMS   = 2        # Solo propiedades de 2+ cuartos
TARGET_ZIPS    = ["33010", "33012"]  # Solo estos ZIPs
MIN_YEAR_BUILT = 1990     # Excluir propiedades muy antiguas
```

### 5. Corre el scraper

```bash
python scripts/scraper.py
```

El scraper corre inmediatamente y luego se repite cada hora de forma automática. Los resultados se guardan en `data/listings_section8.json`.

### 6. Abre el dashboard

```bash
python -m http.server 8080
```

Abre en tu navegador: `http://localhost:8080/dashboard/`

---

## Cómo funciona el filtrado

### Payment Standards 2024

El scraper compara el precio de cada listing contra el Fair Market Rent de HUD para ese ZIP code:

| Resultado | Criterio |
|-----------|----------|
| ✅ Eligible | Precio ≤ FMR del ZIP |
| ⚠️ Near limit | Precio entre FMR y FMR +10% |
| ❌ Over FMR | Precio > FMR +10% |

### Opportunity Score (0–100)

| Factor | Puntos |
|--------|--------|
| Precio dentro del FMR | +50 |
| Precio cerca del FMR (≤10%) | +30 |
| Menciona vouchers en remarks | +25 |
| ZIP de alta demanda de vouchers | +15 |
| 45+ días en mercado | +10 |
| ZIP con transporte público | +10 |

### Filtros adicionales disponibles en `config.py`

- Tipo de propiedad (casa, apartamento, duplex, condo)
- Año de construcción mínimo (evitar pre-1978 por riesgo de plomo)
- Tamaño mínimo/máximo en sq ft
- ZIPs específicos o excluidos
- Días máximos en mercado
- Pesos personalizables del Opportunity Score

---

## Requisitos

- Python 3.9+
- Membresía activa en **Miami Association of Realtors**
- Acceso aprobado a la **Spark API** de MIAMI MLS

---

## Licencia

MIT — uso libre para fines personales y comerciales.
