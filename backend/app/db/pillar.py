from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean
from app.db.session import Base


class Pillar(Base):
    __tablename__ = "pillars"

    id            : Mapped[int]  = mapped_column(Integer, primary_key=True)
    name          : Mapped[str]  = mapped_column(String, unique=True)
    description   : Mapped[str]  = mapped_column(String)
    display_order : Mapped[int]  = mapped_column(Integer)
    is_active     : Mapped[bool] = mapped_column(Boolean, default=True)