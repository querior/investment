
# import sys
# from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from app.db.session import Base, engine as app_engine
from app.core.settings import Settings
from app.db.macro_raw import MacroRaw
from datetime import date
from dateutil.relativedelta import relativedelta
from fastapi.testclient import TestClient
from app.main import app

# ROOT = Path(__file__).resolve().parents[1]
# sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def settings():
    return Settings()
  
@pytest.fixture(scope="session")
def engine():
    Base.metadata.create_all(bind=app_engine)
    yield app_engine
    Base.metadata.drop_all(bind=app_engine)

    
@pytest.fixture(scope="function")
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session
    session.close()
    
@pytest.fixture
def clean_db(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE macro_raw CASCADE"))
        conn.execute(text("TRUNCATE TABLE macro_processed CASCADE"))
        conn.execute(text("TRUNCATE TABLE macro_pillars CASCADE"))
        
        
@pytest.fixture
def macro_raw_monthly_indpro(db_session):
    start = date(2019, 1, 31)
    value = 100.0
    rows = []

    for i in range(24):  # 24 mesi → YoY + window piccoli
        rows.append(
            MacroRaw(
                date=start + relativedelta(months=i),
                indicator="INDPRO",
                value=value,
                source="TEST",
            )
        )
        value *= 1.005  # crescita ~0.5% mensile (realistica)

    db_session.add_all(rows)
    db_session.commit()

    return rows

@pytest.fixture
def client():
    return TestClient(app)