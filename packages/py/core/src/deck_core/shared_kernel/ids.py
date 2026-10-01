"""Identifier types and generation.

Identifiers are UUIDv7 so that primary keys sort by creation time. Distinct
``NewType`` aliases stop a submission id being passed where a tenant id is expected.
"""

import uuid
from typing import NewType, Protocol
from uuid import UUID

TenantId = NewType("TenantId", UUID)
UserId = NewType("UserId", UUID)
EventId = NewType("EventId", UUID)
RubricId = NewType("RubricId", UUID)
RubricVersionId = NewType("RubricVersionId", UUID)
SubmissionId = NewType("SubmissionId", UUID)
UploadId = NewType("UploadId", UUID)
RunId = NewType("RunId", UUID)


class IdGenerator(Protocol):
    def new(self) -> UUID: ...


class Uuid7Generator:
    def new(self) -> UUID:
        return uuid.uuid7()
