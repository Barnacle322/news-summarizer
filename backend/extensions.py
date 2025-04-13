from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Initialize SQLAlchemy
db = SQLAlchemy(
    model_class=Base,
    engine_options={
        "pool_size": 5,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "max_overflow": 6,
    },
)
