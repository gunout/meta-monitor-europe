# 🇪🇺 Meta Monitor Europe

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![httpx](https://img.shields.io/badge/httpx-0.27-0ea5e9)](https://www.python-httpx.org/)
[![Portails](https://img.shields.io/badge/portails-20-blue)](#-portails-supportés)
[![Standards](https://img.shields.io/badge/standards-udata%20%7C%20CKAN%20%7C%20DCAT--AP-green)](#-portails-supportés)
[![Licence](https://img.shields.io/badge/licence-MIT-yellow)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](#-contribuer)

**Méta-moteur de recherche open data européen.** Interroge **20 portails nationaux + data.europa.eu** en parallèle et fusionne les résultats.

---

## 🎯 En bref

| Fonctionnalité | Détail |
|---|---|
| **20 portails** | France, Allemagne, Royaume-Uni, Espagne, Italie, UE… |
| **3 standards** | udata, CKAN, DCAT-AP |
| **Recherche parallèle** | `asyncio.gather` sur toutes les APIs |
| **Déduplication** | Fusion automatique des doublons inter-portails |
| **Cache** | Redis (avec fallback mémoire) |
| **Rate-limit** | 60 req/min par IP |
| **Export** | JSON, CSV |
| **UI** | Interface web moderne (DSFR-like) |

---

## 🚀 Démarrage rapide

### 1. Cloner le dépôt

```bash
git clone https://github.com/gunout/meta-monitor-europe.git
cd meta-monitor-europe
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# ou
venv\Scripts\activate       # Windows
```

### 3. Installer les dépendances

```bash
pip install -r backend/requirements.txt
```

### 4. Lancer le backend

```bash
cd backend
uvicorn europe_meta:app --reload --port 8001
```

**Le backend écoute sur `http://localhost:8001`.**

### 5. Lancer le frontend

**Dans un autre terminal** :

```bash
cd frontend
python3 -m http.server 8080
```

**Ouvrir** : http://localhost:8080

---

## 🌍 Portails supportés

| Pays | Portail | Standard API |
|---|---|---|
| 🇫🇷 France | [data.gouv.fr](https://www.data.gouv.fr) | udata |
| 🇪🇺 Union européenne | [data.europa.eu](https://data.europa.eu) | DCAT-AP |
| 🇩🇪 Allemagne | [govdata.de](https://www.govdata.de) | CKAN |
| 🇬🇧 Royaume-Uni | [data.gov.uk](https://data.gov.uk) | CKAN |
| 🇪🇸 Espagne | [datos.gob.es](https://datos.gob.es) | CKAN |
| 🇮🇹 Italie | [dati.gov.it](https://www.dati.gov.it) | CKAN |
| 🇳🇱 Pays-Bas | [data.overheid.nl](https://data.overheid.nl) | CKAN |
| 🇦🇹 Autriche | [data.gv.at](https://www.data.gv.at) | CKAN |
| 🇧🇪 Belgique | [data.gov.be](https://data.gov.be) | CKAN |
| 🇨🇭 Suisse | [opendata.swiss](https://opendata.swiss) | CKAN |
| 🇵🇹 Portugal | [dados.gov.pt](https://dados.gov.pt) | CKAN |
| 🇮🇪 Irlande | [data.gov.ie](https://data.gov.ie) | CKAN |
| 🇸🇪 Suède | [dataportal.se](https://dataportal.se) | CKAN |
| 🇳🇴 Norvège | [data.norge.no](https://data.norge.no) | CKAN |
| 🇩🇰 Danemark | [opendata.dk](https://portal.opendata.dk) | CKAN |
| 🇫🇮 Finlande | [avoindata.fi](https://avoindata.fi) | CKAN |
| 🇨🇿 Tchéquie | [data.gov.cz](https://data.gov.cz) | CKAN |
| 🇷🇴 Roumanie | [data.gov.ro](https://data.gov.ro) | CKAN |
| 🇵🇱 Pologne | [dane.gov.pl](https://dane.gov.pl) | API custom |
| 🇬🇷 Grèce | [data.gov.gr](https://data.gov.gr) | API custom |

---

## 🔌 API

### `GET /search`

Recherche dans tous les portails sélectionnés.

**Paramètres :**

| Nom | Type | Défaut | Description |
|---|---|---|---|
| `q` | string | `""` | Mot-clé |
| `page` | int | `1` | Numéro de page |
| `page_size` | int | `25` | Résultats par page (max 100) |
| `portals` | string | `all` | CSV de portails (`fr,de,eu`) ou `all` |
| `sort` | enum | `relevance` | `relevance` \| `popularity` \| `recent` |

**Exemple :**

```bash
curl "http://localhost:8001/search?q=transport&portals=fr,de,eu"
```

**Réponse :**

```json
{
  "query": "transport",
  "page": 1,
  "page_size": 25,
  "portals": ["fr", "de", "eu"],
  "sort": "relevance",
  "count": 47,
  "total_raw": 52,
  "total_dedup": 47,
  "duration_ms": 3127,
  "portal_stats": {
    "fr": {"name": "France", "flag": "🇫🇷", "count": 25, "error": null, "duration_ms": 450},
    "de": {"name": "Allemagne", "flag": "🇩🇪", "count": 25, "error": null, "duration_ms": 890}
  },
  "errors": null,
  "results": [...]
}
```

---

### `GET /export`

Export des résultats en CSV ou JSON.

```bash
# CSV
curl "http://localhost:8001/export?q=transport&format=csv&max_pages=5" > resultats.csv

# JSON
curl "http://localhost:8001/export?q=transport&format=json&max_pages=5" > resultats.json
```

---

### `GET /portals`

Liste des portails disponibles.

```bash
curl "http://localhost:8001/portals"
```

---

### `GET /health`

Statut du backend.

```bash
curl "http://localhost:8001/health"
```

**Réponse :**

```json
{
  "status": "ok",
  "portals": 20,
  "cache": {"type": "memory", "connected": false, "keys": 0},
  "ratelimit": {"enabled": true, "requests": 60, "window": 60},
  "auth": {"enabled": false}
}
```

---

### `POST /cache/clear`

Vide le cache.

```bash
curl -X POST "http://localhost:8001/cache/clear"
```

---

## 🏗️ Architecture

```
meta-monitor-europe/
├── backend/
│   ├── europe_meta.py       # FastAPI + 20 portails
│   ├── config.py            # Configuration (env vars)
│   ├── cache.py             # Redis + fallback mémoire
│   ├── ratelimit.py         # 60 req/min par IP
│   ├── auth.py              # API keys (optionnel)
│   └── requirements.txt
├── frontend/
│   └── index.html           # Interface web
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ⚡ Performance

| Métrique | Valeur |
|---|---|
| Requêtes parallèles | 20 |
| Temps moyen (tous portails) | 2-4s |
| Temps moyen (1 portail) | 0.5-1.5s |
| Cache (2ᵉ appel identique) | ~5ms |
| Rate-limit | 60 req/min |

**Exemple mesuré :**

```
$ curl "http://localhost:8001/search?q=transport&portals=fr,de,eu"
{"count": 47, "duration_ms": 3127}
```

---

## 🔒 Sécurité

| Mesure | Détail |
|---|---|
| **Rate-limit** | 60 requêtes/minute par IP |
| **Validation** | URLs validées (anti-SSRF) |
| **Timeout** | 15s par portail |
| **CORS** | Configurable |
| **Auth** | API keys optionnelles |

### Activer l'authentification

```bash
# .env
AUTH_ENABLED=true
API_KEYS=sk_live_xxx,sk_live_yyy
```

Puis :

```bash
curl -H "X-API-Key: sk_live_xxx" "http://localhost:8001/search?q=test"
```

---

## ⚙️ Configuration

Copiez `.env.example` vers `.env` :

```bash
cp .env.example .env
```

**Variables disponibles :**

```env
# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=300

# Rate limiting
RATELIMIT_ENABLED=true
RATELIMIT_REQUESTS=60
RATELIMIT_WINDOW=60

# Auth
AUTH_ENABLED=false
API_KEYS=

# HTTP
HTTP_TIMEOUT=15.0
```

---

## 🐳 Docker

```bash
# Lancer (Redis + backend + frontend)
docker-compose up -d

# Voir les logs
docker-compose logs -f backend

# Arrêter
docker-compose down
```

**Accès :**
- Backend : http://localhost:8001
- Frontend : http://localhost:8080
- API docs : http://localhost:8001/docs

---

## 🧪 Tests

```bash
# Test health
curl http://localhost:8001/health

# Test recherche France
curl "http://localhost:8001/search?q=transport&portals=fr" | python3 -m json.tool

# Test tous portails
curl "http://localhost:8001/search?q=transport&portals=all&page_size=5" | python3 -m json.tool | head -30

# Test rate-limit (60 req)
for i in {1..65}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8001/search?q=test&portals=fr")
  echo "Req $i → $code"
done | tail -10
```

---

## 🛠️ Stack technique

| Composant | Rôle |
|---|---|
| **Python 3.12** | Runtime |
| **FastAPI** 0.115 | Framework web |
| **uvicorn** | Serveur ASGI |
| **httpx** 0.27 | Client HTTP async |
| **redis-py** | Cache (optionnel) |
| **pydantic-settings** | Configuration |

---

## 🤝 Contribuer

Les contributions sont bienvenues !

1. Forkez le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Committez (`git commit -m 'Ajout fonctionnalité'`)
4. Pushez (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📝 Licence

**MIT** — Utilisation libre, y compris commerciale.

---

## 🔗 Liens utiles

- [data.gouv.fr](https://www.data.gouv.fr)
- [data.europa.eu](https://data.europa.eu)
- [CKAN](https://ckan.org)
- [DCAT-AP](https://joinup.ec.europa.eu/collection/semic-support-centre/solution/dcat-application-profile-data-portals-europe)
- [udata](https://udata.readthedocs.io)

---

<p align="center">
  <sub>Fait avec ❤️ pour la communauté open data européenne</sub>
</p>

---

<div align="center">

### 🇫🇷 Gunout · 2026

![Made in France](https://img.shields.io/badge/Made_in-France-002395?style=flat-square&labelColor=FFFFFF&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MDAgNjAwIj48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iIzAwMjM5NSIvPjxyZWN0IHdpZHRoPSI5MDAiIGhlaWdodD0iNDAwIiB5PSIxMDAiIGZpbGw9IiNmZmYiLz48cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjIwMCIgeT0iNDAwIiBmaWxsPSIjZWQyOTM5Ii8+PC9zdmc+)
![GitHub](https://img.shields.io/badge/GitHub-gunout-181717?style=flat-square&logo=github&logoColor=white)
![Year](https://img.shields.io/badge/2026-ED2939?style=flat-square&labelColor=FFFFFF)

<sub>© 2026 <strong>Gunout</strong> — Tous droits réservés.</sub>

</div>
