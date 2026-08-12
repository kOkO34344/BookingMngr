"""Reusable column types."""

from enum import Enum as PyEnum

from sqlalchemy import Enum as SAEnum


def enum_column(enum_cls: type[PyEnum], length: int = 40) -> SAEnum:
    """Store an enum as plain VARCHAR.

    No native PG type and no CHECK constraint, so new members can be added
    without a schema migration.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda e: [member.value for member in e],
        validate_strings=True,
    )
