from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class OptionStrategy(Base):
    __tablename__ = "option_strategies"

    type: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    acronym: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
