"""Uygulamanın "bugün" tarihi. Tarih hesabı yalnızca bu yardımcıdan geçer.

DEMO_TODAY doluysa o gün, boşsa Europe/Istanbul saat dilimindeki takvim günü.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from config.settings import settings

SAAT_DILIMI = ZoneInfo("Europe/Istanbul")


def bugun() -> date:
    """Demo günü ya da İstanbul takvimindeki bugün."""
    if settings.DEMO_TODAY is not None:
        return settings.DEMO_TODAY
    return datetime.now(SAAT_DILIMI).date()
