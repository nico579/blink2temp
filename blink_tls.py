"""Gestion du contexte TLS pour les connexions sécurisées à l'API Blink."""

from __future__ import annotations

import ssl


def contexte_tls() -> ssl.SSLContext:
    """Étend les racines système avec le magasin certifi.

    Garantit une validation TLS stricte pour tous les appels ordinaires aux API Blink.
    """
    contexte = ssl.create_default_context()
    try:
        import certifi
        contexte.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass
    return contexte
