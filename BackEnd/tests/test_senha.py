"""
Testes da recuperação de senha.

O "e-mail" é capturado trocando a função de envio por uma que só guarda o link.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.database import SessionLocal
from app.models import TokenRedefinicaoSenha
from app.services import senha as servico_senha
from tests.conftest import cadastrar_e_logar


@pytest.fixture
def caixa_de_entrada(monkeypatch):
    """Lista onde ficam os links 'enviados' durante o teste."""
    enviados = []
    monkeypatch.setattr(servico_senha, "enviar_link_por_email",
                        lambda email, link: enviados.append((email, link)))
    return enviados


def token_do_link(link):
    return link.split("token=")[1]


def pedir_link(cliente, caixa, email="maria@email.com"):
    cliente.post("/api/auth/esqueci-senha", json={"email": email})
    return token_do_link(caixa[-1][1])


def login_ok(cliente, email, senha):
    return cliente.post("/api/auth/login", data={"username": email, "password": senha}).status_code == 200


def test_fluxo_completo(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com", "senha1234")
    token = pedir_link(cliente, caixa_de_entrada)

    assert caixa_de_entrada[0][0] == "maria@email.com"
    assert caixa_de_entrada[0][1].startswith("http://localhost:8000/redefinir_senha.html?token=")

    resposta = cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "novaSenha99"})
    assert resposta.status_code == 200
    assert login_ok(cliente, "maria@email.com", "novaSenha99")
    assert not login_ok(cliente, "maria@email.com", "senha1234")  # a antiga não vale mais


def test_resposta_igual_para_email_inexistente(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com")
    existe = cliente.post("/api/auth/esqueci-senha", json={"email": "maria@email.com"})
    nao_existe = cliente.post("/api/auth/esqueci-senha", json={"email": "ninguem@email.com"})

    assert existe.status_code == nao_existe.status_code == 200
    assert existe.json() == nao_existe.json()
    assert len(caixa_de_entrada) == 1  # só o e-mail que existe recebeu o link


def test_banco_guarda_so_o_hash_do_token(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com")
    token = pedir_link(cliente, caixa_de_entrada)
    with SessionLocal() as db:
        registro = db.query(TokenRedefinicaoSenha).one()
    assert registro.token_hash != token and len(registro.token_hash) == 64


def test_link_so_pode_ser_usado_uma_vez(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com")
    token = pedir_link(cliente, caixa_de_entrada)
    cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "novaSenha99"})

    segunda = cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "outraSenha1"})
    assert segunda.status_code == 400
    assert login_ok(cliente, "maria@email.com", "novaSenha99")


def test_link_expirado_nao_funciona(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com", "senha1234")
    token = pedir_link(cliente, caixa_de_entrada)
    with SessionLocal() as db:
        db.query(TokenRedefinicaoSenha).one().expira_em = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    resposta = cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "novaSenha99"})
    assert resposta.status_code == 400
    assert login_ok(cliente, "maria@email.com", "senha1234")


def test_pedir_novo_link_cancela_o_anterior(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com")
    antigo = pedir_link(cliente, caixa_de_entrada)
    novo = pedir_link(cliente, caixa_de_entrada)

    assert cliente.post("/api/auth/redefinir-senha",
                        json={"token": antigo, "nova_senha": "novaSenha99"}).status_code == 400
    assert cliente.post("/api/auth/redefinir-senha",
                        json={"token": novo, "nova_senha": "novaSenha99"}).status_code == 200


def test_token_inventado_e_senha_curta(cliente, caixa_de_entrada):
    cadastrar_e_logar(cliente, "maria@email.com")
    token = pedir_link(cliente, caixa_de_entrada)

    inventado = cliente.post("/api/auth/redefinir-senha",
                             json={"token": "x" * 43, "nova_senha": "novaSenha99"})
    assert inventado.status_code == 400

    curta = cliente.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "123"})
    assert curta.status_code == 422 and "Nova senha" in curta.json()["detail"]
    # a tentativa com senha curta não gastou o link
    assert cliente.post("/api/auth/redefinir-senha",
                        json={"token": token, "nova_senha": "novaSenha99"}).status_code == 200
