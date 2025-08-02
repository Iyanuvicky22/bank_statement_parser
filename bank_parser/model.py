import os
import uuid
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import String, Numeric, Date, Text, Integer
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.exc import SQLAlchemyError
from bank_parser.utils.logger import logger

load_dotenv()

DB_URL = os.getenv("DB_URL")

class Base(DeclarativeBase):
    pass


def connect_db():
    try:
        engine = create_engine(DB_URL, echo=True)
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        logger.info("Database successfully connected!!")
        return Session, engine
    except SQLAlchemyError as e:
        logger.error("Error encountered in data loading to database!!!", e)


class BankStatement(Base):

    __tablename__ = 'bank_transactions'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trans_no: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=True)
    date: Mapped[str] = mapped_column(Date, nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(30, 2), nullable=True)
    bank: Mapped[str] = mapped_column(String(100), nullable=True)


def load_data(data: pd.DataFrame) -> pd.DataFrame:
    
    Session, _ = connect_db()
    try:
        with Session.begin() as session:
            for _, row in data.iterrows():
                transaction = (
                    session.query(BankStatement)
                    .filter_by(trans_no=str(row['trans_no']))
                    .first()
                )
                if not transaction:
                    transaction = BankStatement(
                        type=row["type"],
                        trans_no=row['trans_no'],
                        amount=row["amount"],
                        narration=row["narration"],
                        date=row["date"],
                        balance=row["balance"],
                        bank=row["bank"]
                    )
                    session.add(transaction)
            session.commit()
        logger.info("Transactions successfully loaded in database schema!")
    except SQLAlchemyError as e:
        logger.error("Exception error %s", e)
