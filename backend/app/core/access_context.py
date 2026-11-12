"""RLS oturum bağlamı — değerler SQL metnine yazılmadan set_config ile kurulur."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.bugun import bugun


def set_access_context(
    session: Session,
    role: str,
    related_class: str | None,
    related_id: int | None,
) -> None:
    """Mevcut transaction için app.role, app.class, app.student_id ve app.today ayarlar.

    set_config üçüncü argümanı true iken ayar yalnızca bu transaction boyunca
    geçerlidir; SET LOCAL ile aynı kapsamdadır. Değerler :value bağlı
    parametresi olarak gider.

    related_class veya related_id None ise boş string gönderilir. Hafta 1
    politikasındaki NULLIF, boş app.student_id değerini yok sayar.
    """
    class_name = "" if related_class is None else related_class
    student_id = "" if related_id is None else str(related_id)

    session.execute(
        text("SELECT set_config('app.role', :value, true)"),
        {"value": role},
    )
    session.execute(
        text("SELECT set_config('app.class', :value, true)"),
        {"value": class_name},
    )
    session.execute(
        text("SELECT set_config('app.student_id', :value, true)"),
        {"value": student_id},
    )
    # Zaman kapısı: notlar ve devamsızlık politikaları bu günden sonrasını göstermez.
    session.execute(
        text("SELECT set_config('app.today', :value, true)"),
        {"value": bugun().isoformat()},
    )
