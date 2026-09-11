"""Data e hora do domínio, sempre no fuso de São Paulo.

O container roda em UTC, então `date.today()` não serve para decidir "hoje":
das 21h à meia-noite de São Paulo ele já devolve o dia seguinte. Toda validação
de data e hora do sistema passa por aqui.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


SAO_PAULO = ZoneInfo("America/Sao_Paulo")

# Depois desta hora não há mais como produzir e entregar no mesmo dia, então a
# entrega mais próxima passa a ser amanhã.
SAME_DAY_CUTOFF_HOUR = 16


def utcnow() -> datetime:
    """Instante atual em UTC. Para o que é absoluto: expiração de token, log."""
    return datetime.now(timezone.utc)


def as_utc(momento: datetime) -> datetime:
    """Garante datetime com fuso, assumindo UTC quando vier sem.

    O SQLite devolve datetime naive mesmo em coluna declarada com timezone, e
    subtrair naive de aware estoura. No Postgres já vem com fuso, então isto é
    inofensivo lá.
    """
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def now_sp() -> datetime:
    """Instante atual no fuso de São Paulo."""
    return datetime.now(SAO_PAULO)


def today_sp() -> date:
    """Data de hoje em São Paulo."""
    return now_sp().date()


def allows_same_day_delivery() -> bool:
    """Ainda dá para pedir entrega para hoje?"""
    return now_sp().hour < SAME_DAY_CUTOFF_HOUR


def min_scheduled_date() -> date:
    """Primeira data de entrega aceitável.

    Hoje enquanto não passar das 16h de São Paulo; a partir daí, amanhã.
    """
    agora = now_sp()
    if agora.hour >= SAME_DAY_CUTOFF_HOUR:
        return agora.date() + timedelta(days=1)
    return agora.date()
