"""
MLS Section 8 Auto-Search — Miami-Dade
scripts/scraper.py — Motor de búsqueda y filtrado

Personaliza los filtros en config.py sin tocar este archivo.

SETUP:
  pip install -r requirements.txt
  cp .env.template .env   # agrega tus credenciales
  python scripts/scraper.py
"""

import os
import sys
import json
import time
import logging
import schedule
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg

load_dotenv()

Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(cfg.LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def load_payment_standards():
    ps_path = Path(__file__).parent.parent / "data" / "payment_standards_2024.json"
    with open(ps_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["by_zip"], data["default"], data["high_demand_zips"]

BY_ZIP, DEFAULT_STD, HIGH_DEMAND_ZIPS = load_payment_standards()


def get_payment_standard(zip_code: str, bedrooms: int) -> int:
    standards = BY_ZIP.get(str(zip_code), DEFAULT_STD)
    beds = str(min(max(int(bedrooms), 0), 4))
    return int(standards.get(beds, DEFAULT_STD["4"]))


class SparkAPIClient:
    def __init__(self):
        self.client_id     = os.getenv("SPARK_CLIENT_ID")
        self.client_secret = os.getenv("SPARK_CLIENT_SECRET")
        self.base_url      = os.getenv("SPARK_API_URL", "https://api.sparkapi.com")
        self.token         = None
        self.token_expiry  = None
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Faltan credenciales. Crea .env con "
                "SPARK_CLIENT_ID y SPARK_CLIENT_SECRET."
            )

    def _get_token(self):
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.token
        log.info("Obteniendo token OAuth2...")
        resp = requests.post(
            f"{self.base_url}/v1/oauth2/grant",
            data={
                "grant_type":    "client_credentials",
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self.token        = data["access_token"]
        self.token_expiry = datetime.now() + timedelta(
            seconds=data.get("expires_in", 3600) - 60
        )
        return self.token

    def get(self, endpoint, params=None):
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept":        "application/json",
        }
        resp = requests.get(
            f"{self.base_url}{endpoint}",
            headers=headers,
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()


def evaluate_listing(listing: dict) -> dict:
    price      = listing.get("ListPrice", 0) or 0
    beds       = listing.get("BedroomsTotal", 1) or 1
    zip_code   = str(listing.get("PostalCode", ""))
    year_built = listing.get("YearBuilt", 0) or 0
    sqft       = listing.get("LivingArea", 0) or 0
    on_market  = listing.get("OnMarketDate", "") or ""
    remarks    = (listing.get("PublicRemarks") or "").lower()

    standard    = get_payment_standard(zip_code, beds)
    margin      = cfg.FMR_MARGIN_PCT / 100
    max_allowed = round(standard * (1 + margin))
    within_fmr  = price <= standard
    near_fmr    = standard < price <= max_allowed
    over_fmr    = price > max_allowed

    historically_accepts = any(kw in remarks for kw in cfg.ACCEPTANCE_KEYWORDS)

    days_on_market = 0
    if on_market:
        try:
            listed_date    = datetime.fromisoformat(on_market[:10])
            days_on_market = (datetime.now() - listed_date).days
        except Exception:
            pass
    long_on_market   = days_on_market >= 45
    transit_friendly = zip_code in cfg.TRANSIT_FRIENDLY_ZIPS
    lead_paint_risk  = 0 < year_built < 1978

    w = cfg.SCORE_WEIGHTS
    score = 0
    if within_fmr:            score += w.get("within_fmr", 50)
    elif near_fmr:            score += w.get("near_fmr", 30)
    if historically_accepts:  score += w.get("historically_accepts", 25)
    if zip_code in HIGH_DEMAND_ZIPS: score += w.get("high_demand_zip", 15)
    if long_on_market:        score += w.get("long_on_market", 10)
    if transit_friendly:      score += cfg.TRANSIT_SCORE_BONUS
    score = min(score, 100)

    return {
        "eligible":             not over_fmr,
        "status":               "eligible" if within_fmr else ("near_limit" if near_fmr else "over_limit"),
        "payment_standard":     standard,
        "max_allowed":          max_allowed,
        "list_price":           price,
        "gap":                  price - standard,
        "historically_accepts": historically_accepts,
        "high_demand_zip":      zip_code in HIGH_DEMAND_ZIPS,
        "transit_friendly":     transit_friendly,
        "long_on_market":       long_on_market,
        "days_on_market":       days_on_market,
        "lead_paint_risk":      lead_paint_risk,
        "opportunity_score":    score,
    }


def passes_filters(listing: dict, analysis: dict) -> bool:
    beds       = listing.get("BedroomsTotal", 0) or 0
    sqft       = listing.get("LivingArea", 0) or 0
    year_built = listing.get("YearBuilt", 0) or 0
    zip_code   = str(listing.get("PostalCode", ""))

    if beds < cfg.MIN_BEDROOMS:                                             return False
    if cfg.MAX_BEDROOMS and beds > cfg.MAX_BEDROOMS:                        return False
    if cfg.MIN_SQFT and sqft and sqft < cfg.MIN_SQFT:                       return False
    if cfg.MAX_SQFT and sqft and sqft > cfg.MAX_SQFT:                       return False
    if cfg.MIN_YEAR_BUILT and year_built and year_built < cfg.MIN_YEAR_BUILT: return False
    if cfg.TARGET_ZIPS and zip_code not in cfg.TARGET_ZIPS:                 return False
    if zip_code in cfg.EXCLUDE_ZIPS:                                        return False
    if cfg.MAX_DAYS_ON_MARKET and analysis["days_on_market"] > cfg.MAX_DAYS_ON_MARKET: return False
    return True


def fetch_listings(client: SparkAPIClient) -> list:
    all_listings = []
    page         = 1
    page_size    = 100

    zip_filter = ""
    if cfg.TARGET_ZIPS:
        zips       = " or ".join([f"PostalCode eq '{z}'" for z in cfg.TARGET_ZIPS])
        zip_filter = f" and ({zips})"

    log.info("Buscando en MLS — max $%s/mes", cfg.MAX_RENT)

    while True:
        params = {
            "$filter": (
                f"MlsStatus eq 'Active' "
                f"and PropertyType eq 'Residential Lease' "
                f"and CountyOrParish eq 'Miami-Dade' "
                f"and ListPrice le {cfg.MAX_RENT} "
                f"and ListPrice ge {cfg.MIN_RENT}"
                f"{zip_filter}"
            ),
            "$select": ",".join([
                "ListingId","ListPrice","BedroomsTotal","BathroomsTotalDecimal",
                "StreetNumber","StreetName","City","PostalCode","StateOrProvince",
                "PropertyType","PropertySubType","LivingArea","YearBuilt",
                "PublicRemarks","ListAgentFullName","ListAgentEmail",
                "ListOfficeName","StandardStatus","OnMarketDate",
                "Latitude","Longitude","Media",
            ]),
            "$orderby": "OnMarketDate desc",
            "$top":     page_size,
            "$skip":    (page - 1) * page_size,
        }

        try:
            data     = client.get("/v1/listings", params)
            listings = data.get("D", {}).get("Results", [])
            if not listings:
                break
            all_listings.extend(listings)
            log.info("  Página %d — %d listings (total: %d)",
                     page, len(listings), len(all_listings))
            if len(listings) < page_size:
                break
            page += 1
            time.sleep(0.5)
        except requests.HTTPError as e:
            log.error("Error en página %d: %s", page, e)
            break

    return all_listings


def process_listings(raw_listings: list) -> dict:
    results = []
    stats   = {
        "eligible": 0, "near_limit": 0, "over_limit": 0,
        "high_demand": 0, "historically_accepts": 0,
        "transit_friendly": 0, "lead_paint_risk": 0,
    }

    for raw in raw_listings:
        analysis = evaluate_listing(raw)
        if not passes_filters(raw, analysis):
            continue

        media     = raw.get("Media") or []
        photo_url = media[0].get("MediaURL", "") if media else ""

        listing = {
            "id":          raw.get("ListingId"),
            "address":     f"{raw.get('StreetNumber','')} {raw.get('StreetName','')}".strip(),
            "city":        raw.get("City", ""),
            "zip":         raw.get("PostalCode", ""),
            "price":       raw.get("ListPrice", 0),
            "bedrooms":    raw.get("BedroomsTotal", 0),
            "bathrooms":   raw.get("BathroomsTotalDecimal", 0),
            "sqft":        raw.get("LivingArea", 0),
            "year_built":  raw.get("YearBuilt", 0),
            "type":        raw.get("PropertySubType", raw.get("PropertyType", "")),
            "remarks":     (raw.get("PublicRemarks") or "")[:300],
            "agent":       raw.get("ListAgentFullName", ""),
            "agent_email": raw.get("ListAgentEmail", ""),
            "office":      raw.get("ListOfficeName", ""),
            "on_market":   raw.get("OnMarketDate", ""),
            "lat":         raw.get("Latitude"),
            "lng":         raw.get("Longitude"),
            "photo":       photo_url,
            "section8":    analysis,
        }
        results.append(listing)

        s = analysis["status"]
        if s in stats: stats[s] += 1
        if analysis["high_demand_zip"]:      stats["high_demand"] += 1
        if analysis["historically_accepts"]: stats["historically_accepts"] += 1
        if analysis["transit_friendly"]:     stats["transit_friendly"] += 1
        if analysis["lead_paint_risk"]:      stats["lead_paint_risk"] += 1

    results.sort(key=lambda x: x["section8"]["opportunity_score"], reverse=True)

    return {
        "generated_at":   datetime.now().isoformat(),
        "total_raw":      len(raw_listings),
        "total_filtered": len(results),
        "total_eligible": stats["eligible"] + stats["near_limit"],
        "stats":          stats,
        "listings":       results,
    }


def run_search():
    log.info("=" * 55)
    log.info("Búsqueda — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 55)
    try:
        client = SparkAPIClient()
        raw    = fetch_listings(client)
        output = process_listings(raw)

        out_path = Path(__file__).parent.parent / cfg.OUTPUT_FILE
        out_path.parent.mkdir(exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        log.info("Guardado → %s  (%d elegibles)", cfg.OUTPUT_FILE,
                 output["total_eligible"])
    except Exception as e:
        log.exception("Error: %s", e)


if __name__ == "__main__":
    log.info("Scraper iniciado. Intervalo: %d min.", cfg.SEARCH_INTERVAL_MIN)
    run_search()
    schedule.every(cfg.SEARCH_INTERVAL_MIN).minutes.do(run_search)
    while True:
        schedule.run_pending()
        time.sleep(60)
