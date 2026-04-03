from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from app.db.session import Base


class AllocationParameter(Base):
    __tablename__ = "allocation_parameters"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True)
    key         : Mapped[str]   = mapped_column(String, unique=True)
    value       : Mapped[float] = mapped_column(Float)
    description : Mapped[str]   = mapped_column(String)