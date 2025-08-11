from sqlalchemy.orm import DeclarativeBase
from sqlmodel.main import default_registry

Base: DeclarativeBase = default_registry.generate_base()
