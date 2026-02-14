"""Search normalization: lowercase and remove accents for case/accent-insensitive filters."""
import unicodedata


def normalize_search_string(value: str | None) -> str:
    """Normalize string for search: lowercase and remove accents."""
    if not value or not value.strip():
        return ""
    s = value.strip().lower()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def unaccent_like_sql(
    qualified_columns: list[tuple[str, str]],
    param_name: str = "search_pattern",
) -> str:
    """
    Build SQL fragment for accent-insensitive LIKE (PostgreSQL unaccent).
    qualified_columns: [(table_name, column_name), ...] e.g. [("clients", "name")].
    Requires PostgreSQL extension: CREATE EXTENSION unaccent;
    """
    parts = [
        f"unaccent(LOWER({t}.{c})) LIKE :{param_name}"
        for t, c in qualified_columns
    ]
    return "(" + " OR ".join(parts) + ")"
