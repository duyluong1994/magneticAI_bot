"""Database connection and models."""
import enum
from datetime import datetime

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from sqlalchemy import (Boolean, Column, DateTime, Enum, ForeignKey, Integer,
                        Numeric, String, Text, TypeDecorator, create_engine)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Create database URL (using psycopg v3 driver)
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class PaymentStatus(enum.Enum):
    """Payment status enum."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    RETRY_PENDING = 'retry_pending'
    UNCLAIMED = 'unclaimed'


class PaymentStatusType(TypeDecorator):
    """Custom type to handle PaymentStatus enum with PostgreSQL enum type."""
    # Use String as base type - PostgreSQL will handle enum casting
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Convert enum to its value (lowercase string) when saving."""
        if value is None:
            return None
        if isinstance(value, PaymentStatus):
            return value.value  # Return 'pending', 'processing', etc.
        # If already a string, return as is
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert database value to enum when reading."""
        if value is None:
            return None
        # PostgreSQL enum returns as string, convert to enum
        if isinstance(value, str):
            try:
                return PaymentStatus(value.lower())  # Convert 'processing' -> PaymentStatus.PROCESSING
            except ValueError:
                # If value doesn't match any enum, return PENDING as default
                return PaymentStatus.PENDING
        # If already an enum, return as is
        if isinstance(value, PaymentStatus):
            return value
        return value


class Payment(Base):
    """Payment model matching the Node.js Sequelize model."""
    __tablename__ = 'Payments'

    id = Column(UUID(as_uuid=False), primary_key=True)  # UUID stored as string
    userId = Column(UUID(as_uuid=False), ForeignKey('Users.id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    paypalEmail = Column(String, nullable=False)
    paypalTransactionId = Column(String, nullable=True)
    # Use custom type to handle enum conversion
    # Store as String in Python, but PostgreSQL column is enum type
    _status = Column('status', PaymentStatusType(), default=PaymentStatus.PENDING)
    
    @property
    def status(self):
        """Get status as PaymentStatus enum."""
        return self._status
    
    @status.setter
    def status(self, value):
        """Set status from PaymentStatus enum or string."""
        if isinstance(value, PaymentStatus):
            self._status = value
        elif isinstance(value, str):
            try:
                self._status = PaymentStatus(value.lower())
            except ValueError:
                self._status = PaymentStatus.PENDING
        else:
            self._status = value
    type = Column(String, default='cashout')
    transferFee = Column(Numeric(10, 2), default=0.25)
    netAmount = Column(Numeric(10, 2), nullable=False)
    errorMessage = Column(Text, nullable=True)
    processedAt = Column(DateTime, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """User model."""
    __tablename__ = 'Users'

    id = Column(UUID(as_uuid=False), primary_key=True)  # UUID stored as string
    email = Column(String, nullable=False, unique=True)
    currentEarnings = Column(Numeric(10, 2), default=0.00)
    lifetimeEarnings = Column(Numeric(10, 2), default=0.00)
    totalPaidOut = Column(Numeric(10, 2), default=0.00)
    isActive = Column(Boolean, default=True)
    totalPhotosRated = Column(Integer, default=0)
    photosRatedInCurrentBatch = Column(Integer, default=0)
    ratingsInCurrentPeriod = Column(Integer, default=0)


class Rating(Base):
    """Rating model."""
    __tablename__ = 'Ratings'

    id = Column(UUID(as_uuid=False), primary_key=True)  # UUID stored as string
    userId = Column(UUID(as_uuid=False), ForeignKey('Users.id'), nullable=False)
    photoId = Column(UUID(as_uuid=False), ForeignKey('Photos.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    timeInSeconds = Column(Integer, nullable=False)
    startTime = Column(DateTime, nullable=False)
    endTime = Column(DateTime, nullable=False)
    earnings = Column(Numeric(10, 2), nullable=False, default=0.20)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Photo(Base):
    """Photo model."""
    __tablename__ = 'Photos'

    id = Column(UUID(as_uuid=False), primary_key=True)  # UUID stored as string
    imageUrl = Column(String, nullable=False)
    batchId = Column(UUID(as_uuid=False), nullable=False)
    isActive = Column(Boolean, default=True)
    totalRatings = Column(Integer, default=0)
    averageRating = Column(Numeric(3, 2), default=0.00)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

