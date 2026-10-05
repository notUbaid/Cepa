"""
AuditEvent ORM Model.
=====================
Append-only, immutable audit log capturing critical events:
- Calibration overrides
- Defect review overrides
- Report finalization
- Report void / reissue operations
- Security policy checks

Actors must come strictly from authenticated credentials, never client-supplied fields.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Actor identity authenticated from X-Officer-Token or internal system
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="OFFICER")
    # Action verb (e.g. OVERRIDE_CALIBRATION, OVERRIDE_DEFECT, FINALIZE_INSPECTION, VOID_REPORT)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Entity type and ID (e.g. "Inspection:uuid", "Report:uuid", "Bulb:uuid")
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # State capture for full reproducibility
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Immutable append-only timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} actor={self.actor} action={self.action} entity={self.entity_type}:{self.entity_id}>"
