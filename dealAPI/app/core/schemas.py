import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class UUIDSchema(BaseModel):
    uuid: uuid_pkg.UUID = Field(default_factory=uuid_pkg.uuid4)
    
    @field_serializer("uuid")
    def serialize_uuid(self, uuid: uuid_pkg.UUID, _info: Any) -> str:
        """Serialize UUID to string for JSON compatibility"""
        return str(uuid)


class TimestampSchema(BaseModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime | None = Field(default=None)

    @field_serializer("created_at")
    def serialize_dt(self, created_at: datetime | None, _info: Any) -> str | None:
        if created_at is not None:
            return created_at.isoformat()

        return None

    @field_serializer("updated_at")
    def serialize_updated_at(
        self, updated_at: datetime | None, _info: Any
    ) -> str | None:
        if updated_at is not None:
            return updated_at.isoformat()

        return None


class PersistentDeletion(BaseModel):
    deleted_at: datetime | None = Field(default=None)
    is_deleted: bool = False

    @field_serializer("deleted_at")
    def serialize_dates(self, deleted_at: datetime | None, _info: Any) -> str | None:
        if deleted_at is not None:
            return deleted_at.isoformat()

        return None
