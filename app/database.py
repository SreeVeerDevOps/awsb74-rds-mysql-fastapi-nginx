"""
database.py — AWS RDS MySQL connection
Credentials via AWS Secrets Manager | Host/port via AWS SSM Parameter Store
"""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# ── Allow local override via .env / environment variables ─────────────
# Set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD to skip AWS lookups (dev mode)

def _get_aws_secret(secret_name: str, region: str) -> dict:
    """Fetch JSON secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        resp = client.get_secret_value(SecretId=secret_name)
        return json.loads(resp["SecretString"])
    except ClientError as e:
        logger.error(f"Secrets Manager error: {e}")
        raise


def _get_ssm_param(name: str, region: str) -> str:
    """Fetch a single decrypted SSM parameter."""
    client = boto3.client("ssm", region_name=region)
    resp = client.get_parameters(Names=[name], WithDecryption=True)
    params = resp.get("Parameters", [])
    if not params:
        raise ValueError(f"SSM parameter '{name}' not found")
    return params[0]["Value"]


def _build_database_url() -> str:
    """
    Build MySQL connection URL.

    Priority:
      1. Full DATABASE_URL env var (useful for Docker / local dev)
      2. Individual env vars (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD)
      3. AWS Secrets Manager + SSM (production on EC2)
    """
    # Option 1 — direct URL
    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        logger.info("Using DATABASE_URL from environment")
        return direct_url

    # Option 2 — individual env vars (local dev / CI)
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME", "myflixdb")

    if db_host and db_user and db_password:
        logger.info("Using DB credentials from environment variables")
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    # Option 3 — AWS (production)
    region = os.getenv("AWS_REGION", "us-east-1")
    secret_name = os.getenv("SECRET_NAME", "awsb72-rds-creds")
    ssm_host_key = os.getenv("SSM_HOST_KEY", "/b72/db_host")
    ssm_port_key = os.getenv("SSM_PORT_KEY", "/b72/db_port")
    db_name = os.getenv("DB_NAME", "myflixdb")

    logger.info("Fetching DB credentials from AWS Secrets Manager & SSM …")
    secret = _get_aws_secret(secret_name, region)
    db_user = secret["db_user"]
    db_password = secret["db_password"]
    db_host = _get_ssm_param(ssm_host_key, region)
    db_port = _get_ssm_param(ssm_port_key, region)

    logger.info(f"RDS host: {db_host}:{db_port}")
    return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = _build_database_url()


def _ensure_database_exists(url: str) -> None:
    """
    Connect to MySQL *without* specifying a database and create it if missing.
    Handles the (1049, "Unknown database") error automatically.
    """
    try:
        # Strip the database name from the URL to connect to the server root
        from sqlalchemy.engine.url import make_url
        parsed = make_url(url)
        db_name = parsed.database
        root_url = url.replace(f"/{db_name}", "/", 1)

        root_engine = create_engine(root_url, pool_pre_ping=True)
        with root_engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
        root_engine.dispose()
        logger.info(f"✅ Database '{db_name}' is ready")
    except Exception as e:
        logger.warning(f"Could not auto-create database: {e}")


_ensure_database_exists(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # reconnect on dropped connections
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,        # recycle connections every hour
    echo=False,               # set True to log all SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()