# backend/auth.py
# Authentification par API key (optionnelle)
from fastapi import Request, HTTPException, Depends
from config import settings, get_api_keys


async def verify_api_key(request: Request):
    """Si AUTH_ENABLED=true, exige une API key valide."""
    if not settings.auth_enabled:
        return None

    api_key = request.headers.get("X-API-Key", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "API key manquante",
                "hint": "Ajoutez l'en-tête X-API-Key: <votre-clé>"
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )

    valid_keys = get_api_keys()
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=403,
            detail={"error": "API key invalide"}
        )

    return api_key