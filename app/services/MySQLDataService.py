from __future__ import annotations

from .AbstractBaseDataService import AbstractBaseDataService

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


class MySQLDataService(AbstractBaseDataService):
    """Persists records in MySQL DB. Config keys: `mysql_url`, 'table_name", `primary_key_field` (default `customerNumber`)."""

    def __init__(self, config: dict) -> None:
        """
        Initializes the SQLAlchemy engine.
        Format: mysql+pymysql://user:password@host:port/database
        """
        super().__init__(config)
        self._primary_key_field = str(config.get("primary_key_field", "customerNumber"))
        self._table_name = str(config["table_name"])

        self._engine = create_engine(
            config["db_url"],
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self._SessionLocal = sessionmaker(bind=self._engine)


    @contextmanager
    def get_session(self):
        """Provides a transactional scope around a series of operations."""
        session = self._SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def retrieveByPrimaryKey(self, primary_key: str) -> dict:
        with self.get_session() as session:
            sql = text(f"SELECT * FROM {self._table_name} WHERE {self._primary_key_field} = :pk")
            result = session.execute(sql, {"pk": primary_key}).mappings().first()
            return dict(result) if result else {}

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        with self.get_session() as session:
            # Build WHERE clause dynamically: "city = :city AND country = :country"
            if not template:
                where_clause = "1=1"  # Returns everything if template is empty
            else:
                where_clause = " AND ".join([f"{k} = :{k}" for k in template.keys()])

            sql = text(f"SELECT * FROM {self._table_name} WHERE {where_clause}")
            results = session.execute(sql, template).mappings().all()
            return [dict(row) for row in results]

    def create(self, payload: dict) -> str:
        with self.get_session() as session:
            # Check if PK exists in payload, if not, let DB handle it (or use UUID logic)
            # For classicmodels, usually provide the customerNumber

            columns = ", ".join(payload.keys())
            placeholders = ", ".join([f":{k}" for k in payload.keys()])

            sql = text(f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})")
            session.execute(sql, payload)  # If ID exists, raises IntegrityError

            # Return the PK provided in payload, or session.execute("SELECT LAST_INSERT_ID()").scalar()
            return str(payload.get(self._primary_key_field))

    def updateByPrimaryKey(self, primary_key: str, payload: dict) -> int:
        with self.get_session() as session:
            # Build SET clause: "customerName = :customerName, contactFirstName = :contactFirstName"
            set_clause = ", ".join([f"{k} = :{k}" for k in payload.keys()])

            sql = text(f"UPDATE {self._table_name} SET {set_clause} WHERE {self._primary_key_field} = :pk")

            # Merge payload and primary key for binding
            params = {**payload, "pk": primary_key}
            result = session.execute(sql, params)
            return result.rowcount  # Returns 1 if updated, 0 if no record matched the PK

    def deleteByPrimaryKey(self, primary_key: str) -> int:
        with self.get_session() as session:
            sql = text(f"DELETE FROM {self._table_name} WHERE {self._primary_key_field} = :pk")
            result = session.execute(sql, {"pk": primary_key})
            return result.rowcount
