
# import sys
# from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from app.db.session import SessionLocal, Base, engine
from app.core.settings import Settings

# ROOT = Path(__file__).resolve().parents[1]
# sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def settings():
    return Settings()
  
@pytest.fixture(scope="session")
def engine(settings):
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    
@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
  
# @pytest.fixture
# def db_session():
#   Base.metadata.create_all(bind=engine)
#   session = SessionLocal()
#   try:
#     yield session
#   finally:
#     session.rollback()
#     session.close()
    
# @pytest.fixture
# def mock_fred():
#     return MockFred()
  
# class MockFred:
#     def get_series(self, series_id):
#         # serie finta ma realistica
#         idx = pd.date_range(start="2020-01-01", periods=5, freq="ME")
#         return pd.Series([1.0, 1.1, 1.2, 1.3, 1.4], index=idx)