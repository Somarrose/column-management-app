from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
# Define the SQLite database file
DATABASE_URL = "sqlite:///reservations.db"
# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)
# Define Base
Base = declarative_base()
# Define User model
class User(Base):
   __tablename__ = "users"
   id = Column(Integer, primary_key=True, autoincrement=True)
   name = Column(String, nullable=False)
   employee_id = Column(String, unique=True, nullable=False)
   is_admin = Column(Boolean, default=False)
# Define ColumnInfo model
class ColumnInfo(Base):
   __tablename__ = "columns"
   id = Column(Integer, primary_key=True, autoincrement=True)
   sn = Column(String, unique=True, nullable=False)
   reference = Column(String, nullable=False)
   supplier = Column(String, nullable=False)
   dimension = Column(String, nullable=False)
   column_chemistry = Column(String, nullable=False)
   column_number = Column(String, unique=True, nullable=False)
   is_obsolete = Column(Boolean, default=False)
# Define UsageEntry model
class UsageEntry(Base):
   __tablename__ = "usage_entries"
   id = Column(Integer, primary_key=True, autoincrement=True)
   user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
   column_id = Column(Integer, ForeignKey("columns.sn"), nullable=False)
   project = Column(String, nullable=False)
   technique = Column(String, nullable=False)
   mobile_phase_a = Column(String, nullable=False)
   mobile_phase_b = Column(String, nullable=False)
   date = Column(Date, nullable=False)
   user = relationship("User")
   column = relationship("ColumnInfo")
# Create tables
Base.metadata.create_all(engine)
# Reset database by clearing old column records
session = Session()
session.query(ColumnInfo).delete()  # ❌ Delete all existing columns to reset database
session.commit()
session.close()
print("✅ Database initialized successfully! All previous column data cleared.")