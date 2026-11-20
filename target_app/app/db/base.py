from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Every table class inherits from this. It keeps a registry of all tables."""