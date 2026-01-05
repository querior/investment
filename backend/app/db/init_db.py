from app.db.session import engine
from app.db.macro_raw import Base

def init_db():
    Base.metadata.create_all(bind=engine)