
import sys
from pathlib import Path
import pytest
import pandas as pd
from app.db.session import SessionLocal, Base, engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class MockFred:
    def get_series(self, series_id):
        # serie finta ma realistica
        idx = pd.date_range(start="2020-01-01", periods=5, freq="ME")
        return pd.Series([1.0, 1.1, 1.2, 1.3, 1.4], index=idx)

@pytest.fixture
def mock_fred():
    return MockFred()
  
@pytest.fixture
def db_session():
  Base.metadata.create_all(bind=engine)
  session = SessionLocal()
  try:
    yield session
  finally:
    session.rollback()
    session.close()