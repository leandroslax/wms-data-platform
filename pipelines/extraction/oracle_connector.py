from __future__ import annotations

import os
from dataclasses import dataclass

import oracledb


@dataclass
class OracleConfig:
    host: str
    port: int
    sid: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return oracledb.makedsn(
            self.host.strip(),
            self.port,
            sid=self.sid.strip(),
        )


class OracleConnector:
    def __init__(self, config: OracleConfig | None = None) -> None:
        self.config = config or OracleConfig(
            host=os.environ["ORACLE_HOST"].strip(),
            port=int(os.environ.get("ORACLE_PORT", "1521")),
            sid=os.environ["ORACLE_SID"].strip(),
            user=os.environ["ORACLE_USER"].strip(),
            password=os.environ["ORACLE_PASSWORD"],
        )

    def healthcheck(self) -> str:
        with oracledb.connect(
            user=self.config.user,
            password=self.config.password,
            dsn=self.config.dsn,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select 1 from dual")
                row = cursor.fetchone()
        return f"oracle-ok:{row[0]}"

    def execute_query(self, sql: str) -> list[dict]:
        with oracledb.connect(
            user=self.config.user,
            password=self.config.password,
            dsn=self.config.dsn,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [item[0].lower() for item in cursor.description or []]
                rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]
