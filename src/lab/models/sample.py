"""Sample aggregate root.

Physical specimen with a lab-assigned ``accession_code`` (D4 in the schema design).
The synthetic ``id`` is the immutable identity; ``accession_code`` is the lab-owned
value attached to it. Specimen type is free text (D6). No lifecycle column (D5 —
spec is silent on consumption).
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, func
from sqlmodel import Field, SQLModel


class Sample(SQLModel, table=True):
    __tablename__ = "samples"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True),
    )
    accession_code: str = Field(nullable=False, unique=True)
    specimen_type: str = Field(nullable=False)
    collected_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    storage_location: str = Field(nullable=False)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )
