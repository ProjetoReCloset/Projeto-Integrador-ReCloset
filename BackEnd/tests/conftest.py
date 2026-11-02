"""
Configuração dos testes.

Os testes usam um banco SEPARADO (arquivo temporário), então nunca
apagam os dados do seu recloset.db de desenvolvimento.
"""
import os
import tempfile

# Precisa vir ANTES de importar o app, porque config.py lê estas variáveis
_pasta_temp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta_temp}/teste.db"
os.environ["SECRET_KEY"] = "chave-apenas-para-testes-" + "x" * 32
os.environ["PASTA_UPLOADS"] = f"{_pasta_temp}/uploads"
os.environ["TAMANHO_MAX_IMAGEM_MB"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app, preparar_banco


@pytest.fixture
def cliente():
    """Cada teste começa com o banco vazio (só com as categorias)."""
    Base.metadata.drop_all(bind=engine)
    preparar_banco()
    with TestClient(app) as c:
        yield c


def cadastrar_e_logar(cliente, email="maria@email.com", senha="senha1234", nome="Maria Souza"):
    """Ajudante: cria uma conta e devolve o cabeçalho de autorização."""
    cliente.post("/api/auth/cadastro", json={
        "nome": nome, "email": email, "senha": senha, "sexo": "feminino",
    })
    resposta = cliente.post("/api/auth/login", data={"username": email, "password": senha})
    token = resposta.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
