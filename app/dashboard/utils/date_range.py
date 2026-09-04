from datetime import date, datetime, time, timedelta, timezone

# Fuso da operação. O dia de trabalho é o dia no Brasil, não em UTC.
BR_TZ = timezone(timedelta(hours=-3))


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


def resolve_datetime_range(
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime, datetime]:
    """Mesma janela de resolve_date_range, mas em datetime UTC cobrindo o dia inteiro.

    Colunas ``DateTime(timezone=True)`` comparadas com um ``date`` viram meia-noite
    nos dois limites: com o range padrão (hoje, hoje) o BETWEEN só casaria com uma
    linha gravada exatamente às 00:00:00, e o painel fica zerado em silêncio.
    """
    start, end = resolve_date_range(date_from, date_to)

    start_dt = datetime.combine(start, time.min, tzinfo=BR_TZ)
    end_dt = datetime.combine(end, time.max, tzinfo=BR_TZ)

    return start_dt.astimezone(timezone.utc), end_dt.astimezone(timezone.utc)
