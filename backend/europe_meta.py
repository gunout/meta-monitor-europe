# backend/europe_meta.py
import asyncio
import csv
import io
import time
from contextlib import asynccontextmanager
from typing import Literal
import httpx
from fastapi import FastAPI, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from config import settings
from cache import cache
from ratelimit import check_ratelimit, ratelimit_headers
from auth import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.close()


app = FastAPI(title="Meta Monitor Europe — Open Data", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEOUT = httpx.Timeout(settings.http_timeout, connect=5.0)

# ═══════════════════════════════════════════════════════════
#  PORTALAIS (inchangé — 20 portails)
# ═══════════════════════════════════════════════════════════

PORTALS = {
    "fr": {"name": "France", "flag": "🇫🇷", "type": "udata",
           "base": "https://www.data.gouv.fr/api/1",
           "web": "https://www.data.gouv.fr", "search_path": "/datasets/"},
    "eu": {"name": "Union européenne", "flag": "🇪🇺", "type": "dcat",
           "base": "https://data.europa.eu/api/hub/search",
           "web": "https://data.europa.eu", "search_path": "/search"},
    "de": {"name": "Allemagne", "flag": "🇩🇪", "type": "ckan",
           "base": "https://www.govdata.de/ckan/api/3/action",
           "web": "https://www.govdata.de", "search_path": "/package_search"},
    "uk": {"name": "Royaume-Uni", "flag": "🇬🇧", "type": "ckan",
           "base": "https://data.gov.uk/api/3/action",
           "web": "https://data.gov.uk", "search_path": "/package_search"},
    "es": {"name": "Espagne", "flag": "🇪🇸", "type": "ckan",
           "base": "https://datos.gob.es/apidata/catalog",
           "web": "https://datos.gob.es", "search_path": "/dataset"},
    "it": {"name": "Italie", "flag": "🇮🇹", "type": "ckan",
           "base": "https://www.dati.gov.it/opendata/api/3/action",
           "web": "https://www.dati.gov.it", "search_path": "/package_search"},
    "nl": {"name": "Pays-Bas", "flag": "🇳🇱", "type": "ckan",
           "base": "https://data.overheid.nl/api/3/action",
           "web": "https://data.overheid.nl", "search_path": "/package_search"},
    "at": {"name": "Autriche", "flag": "🇦🇹", "type": "ckan",
           "base": "https://www.data.gv.at/katalog/api/3/action",
           "web": "https://www.data.gv.at", "search_path": "/package_search"},
    "be": {"name": "Belgique", "flag": "🇧🇪", "type": "ckan",
           "base": "https://data.gov.be/api/3/action",
           "web": "https://data.gov.be", "search_path": "/package_search"},
    "ch": {"name": "Suisse", "flag": "🇨🇭", "type": "ckan",
           "base": "https://opendata.swiss/api/3/action",
           "web": "https://opendata.swiss", "search_path": "/package_search"},
    "pt": {"name": "Portugal", "flag": "🇵🇹", "type": "ckan",
           "base": "https://dados.gov.pt/api/3/action",
           "web": "https://dados.gov.pt", "search_path": "/package_search"},
    "ie": {"name": "Irlande", "flag": "🇮🇪", "type": "ckan",
           "base": "https://data.gov.ie/api/3/action",
           "web": "https://data.gov.ie", "search_path": "/package_search"},
    "se": {"name": "Suède", "flag": "🇸🇪", "type": "ckan",
           "base": "https://dataportal.se/api/3/action",
           "web": "https://dataportal.se", "search_path": "/package_search"},
    "no": {"name": "Norvège", "flag": "🇳🇴", "type": "ckan",
           "base": "https://data.norge.no/api/3/action",
           "web": "https://data.norge.no", "search_path": "/package_search"},
    "dk": {"name": "Danemark", "flag": "🇩🇰", "type": "ckan",
           "base": "https://portal.opendata.dk/api/3/action",
           "web": "https://portal.opendata.dk", "search_path": "/package_search"},
    "fi": {"name": "Finlande", "flag": "🇫🇮", "type": "ckan",
           "base": "https://avoindata.fi/data/api/3/action",
           "web": "https://avoindata.fi", "search_path": "/package_search"},
    "cz": {"name": "Tchéquie", "flag": "🇨🇿", "type": "ckan",
           "base": "https://data.gov.cz/api/3/action",
           "web": "https://data.gov.cz", "search_path": "/package_search"},
    "ro": {"name": "Roumanie", "flag": "🇷🇴", "type": "ckan",
           "base": "https://data.gov.ro/api/3/action",
           "web": "https://data.gov.ro", "search_path": "/package_search"},
    "pl": {"name": "Pologne", "flag": "🇵🇱", "type": "ckan",
           "base": "https://api.dane.gov.pl/1.4",
           "web": "https://dane.gov.pl", "search_path": "/datasets"},
    "gr": {"name": "Grèce", "flag": "🇬🇷", "type": "ckan",
           "base": "https://data.gov.gr/api/v1",
           "web": "https://data.gov.gr", "search_path": "/datasets"},
}

# ═══════════════════════════════════════════════════════════
#  CONNECTEURS (identiques)
# ═══════════════════════════════════════════════════════════

async def fetch_udata(client, portal, q, page, page_size):
    params = {"page": page, "page_size": page_size}
    if q: params["q"] = q
    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()
    out = []
    for d in data.get("data", []):
        out.append({
            "id": d.get("id"), "title": d.get("title"),
            "description": (d.get("description") or "")[:280],
            "organization": (d.get("organization") or {}).get("name"),
            "url": d.get("page") or f"{portal['web']}/datasets/{d.get('id')}",
            "source_portal": portal["name"], "source_key": portal.get("key", ""),
            "source_flag": portal["flag"], "source_type": "udata",
            "type": "dataset", "tags": d.get("tags", [])[:10],
            "last_update": d.get("last_update"), "popularity": 0,
            "license": d.get("license"), "format": None
        })
    return out


async def fetch_ckan(client, portal, q, page, page_size):
    params = {"rows": page_size, "start": (page - 1) * page_size}
    if q: params["q"] = q
    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"): return []
    out = []
    for d in data.get("result", {}).get("results", []):
        formats = {res.get("format", "").upper() for res in d.get("resources", []) if res.get("format")}
        org = d.get("organization")
        org_name = org.get("title") if isinstance(org, dict) else None
        tracking = d.get("tracking_summary", {})
        popularity = tracking.get("total", 0) if isinstance(tracking, dict) else 0
        out.append({
            "id": d.get("id"), "title": d.get("title"),
            "description": (d.get("notes") or "")[:280],
            "organization": org_name,
            "url": f"{portal['web']}/dataset/{d.get('name') or d.get('id')}",
            "source_portal": portal["name"], "source_key": portal.get("key", ""),
            "source_flag": portal["flag"], "source_type": "ckan",
            "type": "dataset",
            "tags": [t.get("name") for t in d.get("tags", []) if isinstance(t, dict)][:10],
            "last_update": d.get("metadata_modified"),
            "popularity": popularity, "license": d.get("license_title"),
            "format": ", ".join(sorted(formats))[:100] if formats else None
        })
    return out


async def fetch_dcat(client, portal, q, page, page_size):
    params = {"limit": page_size, "page": page - 1}
    if q: params["q"] = q
    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()
    out = []
    for d in data.get("result", {}).get("results", []):
        ds_id = d.get("id") or d.get("identifier")
        title = d.get("title")
        if isinstance(title, dict):
            title = title.get("en") or title.get("fr") or next(iter(title.values()), ds_id)
        publisher = d.get("publisher")
        if isinstance(publisher, dict): publisher = publisher.get("name")
        out.append({
            "id": ds_id, "title": title, "description": "",
            "organization": publisher,
            "url": f"{portal['web']}/data/datasets/{ds_id}",
            "source_portal": portal["name"], "source_key": portal.get("key", ""),
            "source_flag": portal["flag"], "source_type": "dcat",
            "type": "dataset", "tags": [],
            "last_update": d.get("modified"), "popularity": 0,
            "license": None, "format": None
        })
    return out


FETCHERS = {"udata": fetch_udata, "ckan": fetch_ckan, "dcat": fetch_dcat}


async def search_portal(client, portal_key, q, page, page_size):
    portal = dict(PORTALS[portal_key])
    portal["key"] = portal_key
    fetcher = FETCHERS.get(portal["type"])
    if not fetcher:
        return {"portal": portal_key, "results": [], "error": "type inconnu", "duration_ms": 0}
    t0 = time.perf_counter()
    try:
        results = await fetcher(client, portal, q, page, page_size)
        return {"portal": portal_key, "results": results, "error": None,
                "duration_ms": int((time.perf_counter() - t0) * 1000)}
    except httpx.TimeoutException:
        return {"portal": portal_key, "results": [], "error": "timeout",
                "duration_ms": int((time.perf_counter() - t0) * 1000)}
    except httpx.HTTPStatusError as e:
        return {"portal": portal_key, "results": [], "error": f"HTTP {e.response.status_code}",
                "duration_ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as e:
        return {"portal": portal_key, "results": [], "error": str(e)[:100],
                "duration_ms": int((time.perf_counter() - t0) * 1000)}




def _to_str(v):
    """Convertit n'importe quelle valeur (dict multilingue, list, None) en str."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for lang in ("fr", "en", "de", "es", "it"):
            if lang in v and isinstance(v[lang], str):
                return v[lang]
        for val in v.values():
            if isinstance(val, str):
                return val
        return ""
    if isinstance(v, list):
        return " ".join(_to_str(x) for x in v)
    return str(v)


def deduplicate(results):
    seen = {}
    for r in results:
        key = (_to_str(r.get("title"))[:80].lower().strip(),
               _to_str(r.get("organization"))[:40].lower().strip())
        if key not in seen:
            r["title"] = _to_str(r.get("title"))
            r["organization"] = _to_str(r.get("organization"))
            seen[key] = r
        else:
            ex = seen[key]
            ex.setdefault("also_in", []).append({
                "portal": r["source_portal"], "flag": r["source_flag"], "url": r["url"]
            })
    return list(seen.values())


def sort_results(items, sort):
    if sort == "popularity":
        items.sort(key=lambda x: x.get("popularity", 0) or 0, reverse=True)
    elif sort == "recent":
        items.sort(key=lambda x: x.get("last_update") or "", reverse=True)
    return items


async def run_search(q, page, page_size, portals, sort):
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        tasks = [search_portal(client, pk, q, page, page_size)
                 for pk in portals if pk in PORTALS]
        responses = await asyncio.gather(*tasks)

    all_results, errors, portal_stats = [], [], {}
    for resp in responses:
        pk = resp["portal"]
        portal_stats[pk] = {
            "name": PORTALS[pk]["name"], "flag": PORTALS[pk]["flag"],
            "count": len(resp["results"]), "error": resp["error"],
            "duration_ms": resp["duration_ms"]
        }
        if resp["error"]:
            errors.append(f"{PORTALS[pk]['flag']} {PORTALS[pk]['name']}: {resp['error']}")
        all_results.extend(resp["results"])

    merged = deduplicate(all_results)
    merged = sort_results(merged, sort)
    return {"results": merged, "errors": errors, "portal_stats": portal_stats,
            "total_raw": len(all_results), "total_dedup": len(merged)}


# ═══════════════════════════════════════════════════════════
#  ENDPOINTS avec cache + ratelimit + auth
# ═══════════════════════════════════════════════════════════

@app.get("/search")
async def search(
    request: Request,
    q: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    portals: str = Query("all"),
    sort: Literal["relevance", "popularity", "recent"] = Query("relevance"),
    _auth=Depends(verify_api_key),
):
    await check_ratelimit(request)

    if portals == "all":
        selected = list(PORTALS.keys())
    else:
        selected = [p.strip() for p in portals.split(",") if p.strip() in PORTALS]
    if not selected:
        return JSONResponse({"error": "Aucun portail valide"}, status_code=400)

    cache_params = {"q": q, "page": page, "page_size": page_size,
                    "portals": selected, "sort": sort}

    cached = await cache.get("search", cache_params)
    if cached:
        cached["cached"] = True
        return JSONResponse(cached, headers=await ratelimit_headers(request))

    t0 = time.perf_counter()
    result = await run_search(q, page, page_size, selected, sort)
    duration = int((time.perf_counter() - t0) * 1000)

    response = {
        "query": q, "page": page, "page_size": page_size,
        "portals": selected, "sort": sort,
        "count": len(result["results"]),
        "total_raw": result["total_raw"], "total_dedup": result["total_dedup"],
        "duration_ms": duration,
        "portal_stats": result["portal_stats"],
        "errors": result["errors"] or None,
        "results": result["results"],
        "cached": False
    }

    await cache.set("search", cache_params, response, ttl=settings.cache_ttl_seconds)
    return JSONResponse(response, headers=await ratelimit_headers(request))


@app.get("/export")
async def export(
    request: Request,
    q: str = Query(""),
    format: Literal["csv", "json"] = Query("csv"),
    max_pages: int = Query(3, ge=1, le=10),
    page_size: int = Query(50, ge=1, le=100),
    portals: str = Query("all"),
    sort: Literal["relevance", "popularity", "recent"] = Query("popularity"),
    _auth=Depends(verify_api_key),
):
    await check_ratelimit(request)

    if portals == "all":
        selected = list(PORTALS.keys())
    else:
        selected = [p.strip() for p in portals.split(",") if p.strip() in PORTALS]

    all_items, seen, errors = [], set(), []
    for p in range(1, max_pages + 1):
        res = await run_search(q, p, page_size, selected, sort)
        errors.extend(res["errors"])
        for it in res["results"]:
            if it["id"] and it["id"] not in seen:
                seen.add(it["id"])
                all_items.append(it)

    export_items = [{
        "id": it.get("id"), "titre": it.get("title"),
        "portail": it.get("source_portal"), "pays": it.get("source_flag"),
        "type_api": it.get("source_type"), "organisation": it.get("organization"),
        "url": it.get("url"), "tags": ", ".join(it.get("tags") or []),
        "last_update": it.get("last_update"), "popularity": it.get("popularity"),
        "license": it.get("license"), "formats": it.get("format"),
        "description": it.get("description")
    } for it in all_items]

    if format == "json":
        return JSONResponse({"query": q, "total": len(export_items),
                             "errors": errors or None, "results": export_items})

    def generate_csv():
        buffer = io.StringIO()
        fieldnames = ["id", "titre", "portail", "pays", "type_api", "organisation",
                      "url", "tags", "last_update", "popularity", "license",
                      "formats", "description"]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        yield buffer.getvalue()
        buffer.seek(0); buffer.truncate(0)
        for it in export_items:
            writer.writerow(it)
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)

    filename = f"eu_opendata_{(q or 'export').replace(' ', '_')[:40]}.csv"
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/portals")
async def list_portals():
    return {
        "portals": [
            {"key": k, "name": v["name"], "flag": v["flag"],
             "type": v["type"], "web": v["web"]}
            for k, v in PORTALS.items()
        ],
        "count": len(PORTALS)
    }


@app.get("/health")
async def health():
    cache_stats = await cache.stats()
    return {
        "status": "ok",
        "portals": len(PORTALS),
        "cache": cache_stats,
        "ratelimit": {
            "enabled": settings.ratelimit_enabled,
            "requests": settings.ratelimit_requests,
            "window": settings.ratelimit_window
        },
        "auth": {"enabled": settings.auth_enabled}
    }


@app.post("/cache/clear")
async def clear_cache(_auth=Depends(verify_api_key)):
    await cache.clear()
    return {"status": "cleared"}


@app.get("/")
async def root():
    return {
        "message": "Meta Monitor Europe — Open Data",
        "portals": len(PORTALS),
        "endpoints": {
            "search": "/search?q=transport&portals=all&page=1&page_size=25",
            "export_csv": "/export?q=transport&format=csv&max_pages=5",
            "list_portals": "/portals",
            "health": "/health",
            "clear_cache": "POST /cache/clear"
        }
    }