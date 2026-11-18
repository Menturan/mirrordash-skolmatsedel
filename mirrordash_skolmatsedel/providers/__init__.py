"""The data sources. Each provider module has the same functions (see base.py)."""

from mirrordash_skolmatsedel.providers import mateo, skolmaten

PROVIDERS = {"skolmaten": skolmaten, "mateo": mateo}
