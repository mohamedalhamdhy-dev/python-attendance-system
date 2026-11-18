"""MySQL is the production source of truth; SQLite may be used only by isolated tests."""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL=os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL must be set to the local XAMPP MySQL database')
if not DATABASE_URL.startswith('mysql+pymysql://'):
    if not (DATABASE_URL.startswith('sqlite:') and os.environ.get('PRESENCE_TESTING')=='1'):
        raise RuntimeError('Only MySQL is supported outside isolated tests')
kwargs={'pool_pre_ping':True,'pool_recycle':1800}
if DATABASE_URL.startswith('sqlite:'):
    kwargs['connect_args']={'check_same_thread':False}
engine=create_engine(DATABASE_URL,**kwargs)
SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)

class Base(DeclarativeBase):
    pass


def get_db():
    session=SessionLocal()
    try: yield session
    finally:session.close()
