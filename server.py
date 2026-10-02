# europe_meta.py
import asyncio
import csv
import io
from typing import Optional, Literal
import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Meta Monitor Europe — Open Data")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# ═══════════════════════════════════════════════════════════
#  CATALOGUE DES PORTAILS EUROPÉENS
# ═══════════════════════════════════════════════════════════

PORTALS = {
    "fr": {
        "name": "France",
        "flag": "🇫🇷",
        "type": "udata",
        "base": "https://www.data.gouv.fr/api/1",
        "web": "https://www.data.gouv.fr",
        "search_path": "/datasets/",
        "detail_path": "/datasets/{id}/"
    },
    "eu": {
        "name": "Union européenne",
        "flag": "🇪🇺",
        "type": "dcat",
        "base": "https://data.europa.eu/api/hub/search",
        "web": "https://data.europa.eu",
        "search_path": "/search",
        "detail_path": "/datasets/{id}"
    },
    "de": {
        "name": "Allemagne",
        "flag": "🇩🇪",
        "type": "ckan",
        "base": "https://www.govdata.de/ckan/api/3/action",
        "web": "https://www.govdata.de",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "uk": {
        "name": "Royaume-Uni",
        "flag": "🇬🇧",
        "type": "ckan",
        "base": "https://data.gov.uk/api/3/action",
        "web": "https://data.gov.uk",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "es": {
        "name": "Espagne",
        "flag": "🇪🇸",
        "type": "ckan",
        "base": "https://datos.gob.es/apidata/catalog",
        "web": "https://datos.gob.es",
        "search_path": "/dataset",
        "detail_path": "/dataset/{id}"
    },
    "it": {
        "name": "Italie",
        "flag": "🇮🇹",
        "type": "ckan",
        "base": "https://www.dati.gov.it/opendata/api/3/action",
        "web": "https://www.dati.gov.it",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "nl": {
        "name": "Pays-Bas",
        "flag": "🇳🇱",
        "type": "ckan",
        "base": "https://data.overheid.nl/api/3/action",
        "web": "https://data.overheid.nl",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "at": {
        "name": "Autriche",
        "flag": "🇦🇹",
        "type": "ckan",
        "base": "https://www.data.gv.at/katalog/api/3/action",
        "web": "https://www.data.gv.at",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "be": {
        "name": "Belgique",
        "flag": "🇧🇪",
        "type": "ckan",
        "base": "https://data.gov.be/api/3/action",
        "web": "https://data.gov.be",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    },
    "ch": {
        "name": "Suisse",
        "flag": "🇨🇭",
        "type": "ckan",
        "base": "https://opendata.swiss/api/3/action",
        "web": "https://opendata.swiss",
        "search_path": "/package_search",
        "detail_path": "/package_show"
    }
}

# ═══════════════════════════════════════════════════════════
#  CONNECTEURS PAR TYPE D'API
# ═══════════════════════════════════════════════════════════

async def fetch_udata(client, portal, q, page, page_size):
    """data.gouv.fr (udata)"""
    params = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()

    results = []
    for d in data.get("data", []):
        results.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "description": (d.get("description") or "")[:280],
            "organization": (d.get("organization") or {}).get("name"),
            "url": d.get("page") or f"{portal['web']}/datasets/{d.get('id')}",
            "source_portal": portal["name"],
            "source_flag": portal["flag"],
            "source_type": "udata",
            "type": "dataset",
            "tags": d.get("tags", [])[:10],
            "last_update": d.get("last_update"),
            "popularity": 0,
            "license": d.get("license"),
            "format": None
        })
    return results


async def fetch_ckan(client, portal, q, page, page_size):
    """Portails CKAN (Allemagne, UK, Italie, etc.)"""
    params = {
        "rows": page_size,
        "start": (page - 1) * page_size
    }
    if q:
        params["q"] = q

    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()

    if not data.get("success"):
        return []

    results = []
    for d in data.get("result", {}).get("results", []):
        formats = set()
        for res in d.get("resources", []):
            if res.get("format"):
                formats.add(res["format"].upper())

        results.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "description": (d.get("notes") or "")[:280],
            "organization": d.get("organization", {}).get("title") if isinstance(d.get("organization"), dict) else None,
            "url": f"{portal['web']}/dataset/{d.get('name') or d.get('id')}",
            "source_portal": portal["name"],
            "source_flag": portal["flag"],
            "source_type": "ckan",
            "type": "dataset",
            "tags": [t.get("name") for t in d.get("tags", []) if isinstance(t, dict)][:10],
            "last_update": d.get("metadata_modified"),
            "popularity": d.get("tracking_summary", {}).get("total", 0) if isinstance(d.get("tracking_summary"), dict) else 0,
            "license": d.get("license_title"),
            "format": ", ".join(sorted(formats))[:100] if formats else None
        })
    return results


async def fetch_dcat(client, portal, q, page, page_size):
    """data.europa.eu (DCAT-AP)"""
    params = {
        "limit": page_size,
        "page": page - 1
    }
    if q:
        params["q"] = q

    r = await client.get(f"{portal['base']}{portal['search_path']}", params=params)
    r.raise_for_status()
    data = r.json()

    results = []
    for d in data.get("result", {}).get("results", []):
        ds_id = d.get("id") or d.get("identifier")
        title = d.get("title")
        if isinstance(title, dict):
            title = title.get("en") or title.get("fr") or next(iter(title.values()), ds_id)

        publisher = d.get("publisher")
        if isinstance(publisher, dict):
            publisher = publisher.get("name")

        results.append({
            "id": ds_id,
            "title": title,
            "description": "",
            "organization": publisher,
            "url": f"{portal['web']}/data/datasets/{ds_id}",
            "source_portal": portal["name"],
            "source_flag": portal["flag"],
            "source_type": "dcat",
            "type": "dataset",
            "tags": [],
            "last_update": d.get("modified"),
            "popularity": 0,
            "license": None,
            "format": None
        })
    return results


FETCHERS = {
    "udata": fetch_udata,
    "ckan": fetch_ckan,
    "dcat": fetch_dcat,
}


async def search_portal(client, portal_key, q, page, page_size):
    portal = PORTALS[portal_key]
    fetcher = FETCHERS.get(portal["type"])
    if not fetcher:
        return {"portal": portal_key, "results": [], "error": f"Type inconnu: {portal['type']}"}

    try:
        results = await fetcher(client, portal, q, page, page_size)
        return {"portal": portal_key, "results": results, "error": None}
    except httpx.TimeoutException:
        return {"portal": portal_key, "results": [], "error": "timeout"}
    except httpx.HTTPStatusError as e:
        return {"portal": portal_key, "results": [], "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"portal": portal_key, "results": [], "error": str(e)[:100]}


# ═══════════════════════════════════════════════════════════
#  DÉDUPLICATION INTER-PORTAILS
# ═══════════════════════════════════════════════════════════

def deduplicate(results):
    """Fusionne les doublons (même titre normalisé + même org)"""
    seen = {}
    for r in results:
        key = (
            (r.get("title") or "").lower().strip()[:80],
            (r.get("organization") or "").lower().strip()[:40]
        )
        if key not in seen:
            seen[key] = r
        else:
            existing = seen[key]
            if "also_in" not in existing:
                existing["also_in"] = []
            existing["also_in"].append({
                "portal": r["source_portal"],
                "flag": r["source_flag"],
                "url": r["url"]
            })
    return list(seen.values())


def sort_results(items, sort):
    if sort == "popularity":
        items.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    elif sort == "recent":
        items.sort(key=lambda x: x.get("last_update") or "", reverse=True)
    return items


# ═══════════════════════════════════════════════════════════
#  MOTEUR DE RECHERCHE
# ═══════════════════════════════════════════════════════════

async def run_search(q, page, page_size, portals, sort):
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        tasks = [
            search_portal(client, pk, q, page, page_size)
            for pk in portals
            if pk in PORTALS
        ]
        responses = await asyncio.gather(*tasks)

    all_results = []
    errors = []
    portal_stats = {}

    for resp in responses:
        pk = resp["portal"]
        portal_stats[pk] = {
            "name": PORTALS[pk]["name"],
            "flag": PORTALS[pk]["flag"],
            "count": len(resp["results"]),
            "error": resp["error"]
        }
        if resp["error"]:
            errors.append(f"{PORTALS[pk]['name']}: {resp['error']}")
        all_results.extend(resp["results"])

    merged = deduplicate(all_results)
    merged = sort_results(merged, sort)

    return {
        "results": merged,
        "errors": errors,
        "portal_stats": portal_stats,
        "total_raw": len(all_results),
        "total_dedup": len(merged)
    }


# ═══════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/search")
async def search(
    q: str = Query("", description="Mot-clé"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    portals: str = Query("all", description="Liste CSV: fr,de,uk,eu,... ou 'all'"),
    sort: Literal["relevance", "popularity", "recent"] = Query("relevance"),
):
    if portals == "all":
        selected = list(PORTALS.keys())
    else:
        selected = [p.strip() for p in portals.split(",") if p.strip() in PORTALS]

    if not selected:
        return JSONResponse({"error": "Aucun portail valide"}, status_code=400)

    result = await run_search(q, page, page_size, selected, sort)
    return JSONResponse({
        "query": q,
        "page": page,
        "page_size": page_size,
        "portals": selected,
        "sort": sort,
        "count": len(result["results"]),
        "total_raw": result["total_raw"],
        "total_dedup": result["total_dedup"],
        "portal_stats": result["portal_stats"],
        "errors": result["errors"] or None,
        "results": result["results"]
    })


@app.get("/export")
async def export(
    q: str = Query(""),
    format: Literal["csv", "json"] = Query("csv"),
    max_pages: int = Query(3, ge=1, le=10),
    page_size: int = Query(50, ge=1, le=100),
    portals: str = Query("all"),
    sort: Literal["relevance", "popularity", "recent"] = Query("popularity"),
):
    if portals == "all":
        selected = list(PORTALS.keys())
    else:
        selected = [p.strip() for p in portals.split(",") if p.strip() in PORTALS]

    all_items = []
    seen = set()
    errors = []

    for p in range(1, max_pages + 1):
        res = await run_search(q, p, page_size, selected, sort)
        errors.extend(res["errors"])
        for it in res["results"]:
            key = it["id"]
            if key not in seen:
                seen.add(key)
                all_items.append(it)

    export_items = []
    for it in all_items:
        export_items.append({
            "id": it.get("id"),
            "titre": it.get("title"),
            "portail": it.get("source_portal"),
            "pays": it.get("source_flag"),
            "type_api": it.get("source_type"),
            "organisation": it.get("organization"),
            "url": it.get("url"),
            "tags": ", ".join(it.get("tags") or []),
            "last_update": it.get("last_update"),
            "popularity": it.get("popularity"),
            "license": it.get("license"),
            "formats": it.get("format"),
            "description": it.get("description")
        })

    if format == "json":
        return JSONResponse({
            "query": q,
            "total": len(export_items),
            "errors": errors or None,
            "results": export_items
        })

    def generate_csv():
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=list(export_items[0].keys()) if export_items else [
                "id", "titre", "portail", "pays", "type_api", "organisation",
                "url", "tags", "last_update", "popularity", "license", "formats", "description"
            ],
            quoting=csv.QUOTE_ALL
        )
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
            {
                "key": k,
                "name": v["name"],
                "flag": v["flag"],
                "type": v["type"],
                "web": v["web"]
            }
            for k, v in PORTALS.items()
        ],
        "count": len(PORTALS)
    }


@app.get("/")
async def root():
    return {
        "message": "Meta Monitor Europe — Open Data",
        "portals": len(PORTALS),
        "endpoints": {
            "search": "/search?q=transport&portals=all&page=1&page_size=25",
            "search_fr_de": "/search?q=transport&portals=fr,de",
            "export_csv": "/export?q=transport&format=csv&max_pages=5",
            "list_portals": "/portals"
        }
    }