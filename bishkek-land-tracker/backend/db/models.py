from datetime import date
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    avg_price_per_sotka: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_price_per_sotka: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)

    listings: Mapped[list["Listing"]] = relationship(back_populates="district")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), nullable=False)
    area_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    current_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    first_seen: Mapped[date] = mapped_column(Date, nullable=False)
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    district: Mapped["District"] = relationship(back_populates="listings")
    history: Mapped[list["PriceHistory"]] = relationship(back_populates="listing")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_sotka: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    change_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    listing: Mapped["Listing"] = relationship(back_populates="history")


class MacroData(Base):
    __tablename__ = "macro_data"
    __table_args__ = (UniqueConstraint("recorded_at", "source", name="uq_macro_date_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    usd_kgs_rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)
