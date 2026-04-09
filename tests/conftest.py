"""
tests/conftest.py
-----------------
Shared fixtures: in-memory SQLite DB, FastAPI test client, sample data factories.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Must be set before api.main is imported so the lifespan JWT guard passes.
os.environ.setdefault("JWT_SECRET", "a" * 32)

from api.auth import get_current_user, reset_login_rate_limits
from api.db import Base, get_db
from api.models import AccountModel, SignalModel, TradeModel

TEST_USER = "testuser"
TEST_USER_2 = "otheruser"

_TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_TEST_ENGINE, autocommit=False, autoflush=False)


def _override_get_db() -> Generator[Session, None, None]:
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


def _override_get_current_user() -> str:
    return TEST_USER


@pytest.fixture(autouse=True)
def _setup_tables() -> Generator[None, None, None]:
    """Create all tables before each test and drop them after."""
    reset_login_rate_limits()
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Yield a test DB session."""
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """FastAPI test client wired to the in-memory DB as TEST_USER."""
    from api.main import app

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture()
def raw_client() -> Generator[TestClient, None, None]:
    """Test client with real JWT validation (get_current_user NOT overridden)."""
    from api.main import app

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client_other_user() -> Generator[TestClient, None, None]:
    """FastAPI test client wired to the in-memory DB as TEST_USER_2."""
    from api.main import app

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: TEST_USER_2
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_account(db: Session) -> AccountModel:
    """Insert and return a single demo account owned by TEST_USER."""
    account = AccountModel(
        id=str(uuid.uuid4()),
        name="Test Demo",
        account_type="demo",
        instrument_type="forex",
        status="active",
        prop_firm=None,
        phase=None,
        owner=TEST_USER,
        created_at=datetime.now(timezone.utc),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture()
def sample_signal(db: Session) -> SignalModel:
    """Insert and return a single signal."""
    signal = SignalModel(
        id=str(uuid.uuid4()),
        strategy="fvg-impulse",
        symbol="EURUSD",
        direction="BUY",
        candle_time=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        entry=1.08500,
        sl=1.08200,
        tp=1.09100,
        lot_size=0.50,
        risk_pips=30.0,
        spread_pips=1.2,
        signal_metadata={"fvg_size": 15},
        created_at=datetime.now(timezone.utc),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def make_trade(
    db: Session,
    *,
    owner: str = TEST_USER,
    strategy: str = "fvg-impulse",
    symbol: str = "EURUSD",
    direction: str = "BUY",
    entry_price: float = 1.08500,
    exit_price: float | None = None,
    sl_price: float = 1.08200,
    tp_price: float | None = 1.09100,
    lot_size: float = 0.50,
    status: str = "open",
    outcome: str | None = None,
    pnl_pips: float | None = None,
    pnl_usd: float | None = None,
    rr_achieved: float | None = None,
    risk_pips: float = 30.0,
    open_time: datetime | None = None,
    close_time: datetime | None = None,
    account_id: str | None = None,
    instrument_type: str = "forex",
) -> TradeModel:
    """Insert and return a trade with sensible defaults."""
    now = datetime.now(timezone.utc)
    trade = TradeModel(
        id=str(uuid.uuid4()),
        signal_id=None,
        account_id=account_id,
        owner=owner,
        strategy=strategy,
        symbol=symbol,
        instrument_type=instrument_type,
        direction=direction,
        entry_price=entry_price,
        exit_price=exit_price,
        sl_price=sl_price,
        tp_price=tp_price,
        lot_size=lot_size,
        status=status,
        outcome=outcome,
        pnl_pips=pnl_pips,
        pnl_usd=pnl_usd,
        rr_achieved=rr_achieved,
        risk_pips=risk_pips,
        open_time=open_time or now,
        close_time=close_time,
        tags=[],
        notes="",
        rating=None,
        confidence=None,
        screenshot_url=None,
        trade_metadata={},
        created_at=now,
        updated_at=now,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
