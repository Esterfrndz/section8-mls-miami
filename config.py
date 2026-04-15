# ─────────────────────────────────────────────────────
# config.py — Personaliza aquí todos los filtros
# No necesitas tocar scraper.py para cambiar criterios
# ─────────────────────────────────────────────────────

# ── Búsqueda general ──────────────────────────────────
MAX_RENT            = 3500      # Precio máximo a consultar en el MLS
SEARCH_INTERVAL_MIN = 60        # Frecuencia de búsqueda (minutos)
OUTPUT_FILE         = "data/listings_section8.json"
LOG_FILE            = "logs/mls_search.log"

# ── Filtros de propiedad ──────────────────────────────
PROPERTY_TYPES = [
    "Residential Lease",        # Incluye todos por defecto
    # "Single Family",          # Descomenta para solo casas
    # "Multifamily",
    # "Condominium",
    # "Duplex",
    # "Townhouse",
]

MIN_BEDROOMS  = 1               # Mínimo de cuartos (0 = studio)
MAX_BEDROOMS  = 5               # Máximo de cuartos

MIN_SQFT      = 400             # Tamaño mínimo en sq ft (0 = sin límite)
MAX_SQFT      = 0               # 0 = sin límite

MIN_YEAR_BUILT = 0              # 0 = sin límite | ej: 1990
# Nota: propiedades anteriores a 1978 requieren inspección de plomo

# ── Filtros de precio ─────────────────────────────────
FMR_MARGIN_PCT = 10             # % permitido sobre el FMR (HUD permite hasta 10%)
MIN_RENT       = 800            # Renta mínima a considerar

# ── Filtros de timing ─────────────────────────────────
MAX_DAYS_ON_MARKET = 0          # 0 = sin límite | ej: 60 días en mercado
# Propiedades con 45+ días suelen tener propietarios más flexibles

# ── Filtros de zona ───────────────────────────────────
# Dejar vacío [] = buscar en todo Miami-Dade
# Llenar con ZIPs específicos para acotar la búsqueda
TARGET_ZIPS = []
# Ejemplo: TARGET_ZIPS = ["33010", "33012", "33147", "33030"]

EXCLUDE_ZIPS = []               # ZIPs a excluir de resultados

# ── Oportunidad — pesos del score ────────────────────
# Total siempre suma 100. Ajusta según tu estrategia.
SCORE_WEIGHTS = {
    "within_fmr":           50, # Precio dentro del Payment Standard
    "near_fmr":             30, # Precio cerca del límite (dentro del margen)
    "historically_accepts": 25, # Menciona vouchers/Sección 8 en remarks
    "high_demand_zip":      15, # ZIP con alta concentración de voucher holders
    "long_on_market":       10, # 45+ días en mercado = propietario más flexible
    # Nota: el score se capea en 100
}

# ── Keywords de aceptación histórica ─────────────────
# El scraper busca estas palabras en los remarks del listing
ACCEPTANCE_KEYWORDS = [
    "section 8",
    "section8",
    "housing voucher",
    "housing choice voucher",
    "hcv",
    "hacd",
    "voucher welcome",
    "voucher accepted",
    "vouchers accepted",
    "subsidized",
    "government assistance",
    "plan 8",
    "hud approved",
]

# ── Notificaciones por email ──────────────────────────
# Requiere configurar SMTP en .env
NOTIFY_EMAIL_ENABLED    = False
NOTIFY_MIN_SCORE        = 85    # Solo notifica listings con score >= este valor
NOTIFY_MAX_PER_RUN      = 5     # Máximo de listings por email

# ── Transporte público ────────────────────────────────
# Futura integración con Miami-Dade Transit API
# Por ahora marca ZIPs con buena cobertura de Metrobus/Metrorail
TRANSIT_FRIENDLY_ZIPS = [
    "33010", "33012", "33030", "33054",  # Metrobus principal
    "33125", "33126", "33127", "33128",  # Cercanía Metrorail
    "33136", "33142", "33147", "33150",  # Corredores Brickell/NW
    "33161", "33167", "33168", "33169",  # North Miami corridors
]
TRANSIT_SCORE_BONUS = 10        # Puntos extra por ZIP con buen transporte
