from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_URL = "postgresql://postgres:password@localhost/jss"

engine = create_engine(DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)