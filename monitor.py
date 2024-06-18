"""Comprueba la conexión a MySQL y reinicia el túnel SSH si es necesario."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("Tunnel Monitor")
logging.basicConfig(level=logging.INFO)

SIGNAL_FILE = Path("/tmp/tunnel_ready")  # noqa: S108


@dataclass
class TunnelParams:
    """Parameters for the SSH tunnel to the database."""

    ssh_host: str
    ssh_port: int
    ssh_user: str
    ssh_private_key: str
    db_host: str
    db_port: int
    ssh_key_path: str


def get_tunnel_params() -> TunnelParams:
    """Read the SSH tunnel parameters from environment variables."""
    return TunnelParams(
        ssh_host=os.getenv("SSH_HOST", "ssh"),
        ssh_port=int(os.getenv("SSH_PORT", "22")),
        ssh_user=os.getenv("SSH_USER", "root"),
        ssh_private_key=os.getenv("SSH_PRIVATE_KEY", ""),
        ssh_key_path=os.getenv("SSH_KEY_PATH", "/root/.ssh/id_rsa"),
        db_host=os.getenv("DB_HOST", "mariadb"),
        db_port=int(os.getenv("DB_PORT", "3306")),
    )


def check_db_connection(uri: str) -> bool:
    """Check if a database connection can be established using SQLAlchemy."""
    try:
        engine = create_engine(uri)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.error("Falló la comprobación de la conexión a la base de datos")  # noqa: TRY400
        return False
    else:
        return True


def create_key_file(tunnel_params: TunnelParams) -> None:
    """Create the SSH private key file."""
    tp = tunnel_params
    key_path = Path(tp.ssh_key_path)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with key_path.open("w") as key_file:
        key_file.write(tp.ssh_private_key + "\n")
    key_path.chmod(0o600)


def restart_ssh_tunnel(tunnel_params: TunnelParams) -> subprocess.Popen | None:
    """Restart the SSH tunnel to the database."""
    tp = tunnel_params
    ssh_command = [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-N",
        "-L",
        f"127.0.0.1:{tp.db_port}:{tp.db_host}:{tp.db_port}",
        "-p",
        str(tp.ssh_port),
        f"{tp.ssh_user}@{tp.ssh_host}",
        "-i",
        tp.ssh_key_path,
    ]
    logger.info("Restarting tunnel with: %s", " ".join(ssh_command))
    try:
        process = subprocess.Popen(ssh_command)  # noqa: S603
    except Exception:
        logger.exception("Failed to start SSH tunnel")
        return None

    time.sleep(5)
    return process


# Singleton class to calculate reattempt time
class ReattemptTime:
    """Calculate the time to reattempt a connection."""

    def __init__(self) -> None:
        """Initialize the reattempt time to 1 second."""
        self.reattempt_time = 1

    def __call__(self) -> float:
        """Calculate the reattempt time and double it for the next call."""
        self.reattempt_time = min(self.reattempt_time * 2, 60)
        return self.reattempt_time

    def reset(self) -> None:
        """Reset the reattempt time to 1 second."""
        self.reattempt_time = 1


def create_signal_file() -> None:
    """Create a signal file to indicate the tunnel is ready."""
    if SIGNAL_FILE.exists():
        return
    with SIGNAL_FILE.open("w") as f:
        f.write("Tunnel is ready\n")
    logger.info("Tunnel is ready. Signal file %s created", SIGNAL_FILE)


def remove_signal_file() -> None:
    """Remove the signal file to indicate the tunnel is not ready."""
    if SIGNAL_FILE.exists():
        SIGNAL_FILE.unlink()


def monitor_connection() -> None:
    """Monitor db connection and restart the SSH tunnel if necessary."""
    tunnel_params = get_tunnel_params()
    db_uri = os.getenv(
        "FLASK_SQLALCHEMY_DATABASE_URI",
        "mysql://root:root@localhost:3306",
    )
    create_key_file(tunnel_params)
    timer = ReattemptTime()
    tunnel_process = restart_ssh_tunnel(tunnel_params)

    while True:
        if not check_db_connection(db_uri):
            if tunnel_process:
                tunnel_process.terminate()
                tunnel_process.wait()
            remove_signal_file()
            cool_down = timer()
            logger.info("Retrying in %d seconds", cool_down)
            time.sleep(cool_down)
            tunnel_process = restart_ssh_tunnel(tunnel_params)
        else:
            create_signal_file()
            timer.reset()
            time.sleep(60)


if __name__ == "__main__":
    monitor_connection()
