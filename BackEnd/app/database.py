"""
Conexão com o banco de dados (SQLAlchemy).
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

eh_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    # O SQLite, por padrão, só aceita a thread que abriu a conexão.
    # O FastAPI usa várias threads, então liberamos isso.
    connect_args={"check_same_thread": False} if eh_sqlite else {},
)

if eh_sqlite:
    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao, _registro):
        # O SQLite vem com as FOREIGN KEYs DESLIGADAS por padrão.
        # Sem isso, daria para criar um produto de um usuário que não existe.
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Fábrica de sessões: cada requisição abre uma sessão e fecha no final.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe-mãe de todos os modelos (tabelas)."""


def get_db():
    """
    Dependência do FastAPI: entrega uma sessão para a rota
    e garante que ela será fechada, mesmo se der erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
