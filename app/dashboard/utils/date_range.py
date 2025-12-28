from datetime import date


def resolve_date_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    today = date.today()

    if not date_from and not date_to:
        return today, today

    if date_from and not date_to:
        return date_from, date_from

    if not date_from and date_to:
        return date_to, date_to

    return date_from, date_to
