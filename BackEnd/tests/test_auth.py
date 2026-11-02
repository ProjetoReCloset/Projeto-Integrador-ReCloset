"""
Testes de cadastro, login e perfil.

Rodar (dentro de BackEnd/):   python -m pytest -v
"""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Usuario
from tests.conftest import cadastrar_e_logar

DADOS = {"nome": "Maria Souza", "email": "maria@email.com", "senha": "senha1234", "sexo": "feminino"}


def test_cadastro_cria_usuario_sem_expor_senha(cliente):
    resposta = cliente.post("/api/auth/cadastro", json=DADOS)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["email"] == "maria@email.com"
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_senha_e_guardada_como_hash(cliente):
    cliente.post("/api/auth/cadastro", json=DADOS)

    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == "maria@email.com"))
    assert usuario.senha_hash != "senha1234"
    assert usuario.senha_hash.startswith("$2b$")  # formato do bcrypt


def test_email_duplicado_e_recusado_mesmo_com_maiusculas(cliente):
    cliente.post("/api/auth/cadastro", json=DADOS)
    resposta = cliente.post("/api/auth/cadastro", json={**DADOS, "email": "MARIA@Email.com"})

    assert resposta.status_code == 409


def test_cadastro_valida_campos(cliente):
    resposta = cliente.post("/api/auth/cadastro", json={
        "nome": "M", "email": "nao-e-email", "senha": "123", "sexo": "x",
    })

    assert resposta.status_code == 422
    mensagem = resposta.json()["detail"]
    for campo in ("Nome", "E-mail", "Senha", "Sexo"):
        assert campo in mensagem


def test_login_com_senha_errada_falha(cliente):
    cliente.post("/api/auth/cadastro", json=DADOS)
    resposta = cliente.post("/api/auth/login", data={"username": DADOS["email"], "password": "errada123"})

    assert resposta.status_code == 401


def test_login_com_email_inexistente_tem_a_mesma_mensagem(cliente):
    cliente.post("/api/auth/cadastro", json=DADOS)
    errada = cliente.post("/api/auth/login", data={"username": DADOS["email"], "password": "errada123"})
    inexistente = cliente.post("/api/auth/login", data={"username": "ninguem@email.com", "password": "x"})

    assert errada.json() == inexistente.json()


def test_rota_privada_exige_token(cliente):
    assert cliente.get("/api/usuarios/me").status_code == 401
    falso = {"Authorization": "Bearer token-inventado"}
    assert cliente.get("/api/usuarios/me", headers=falso).status_code == 401


def test_me_devolve_o_usuario_do_token(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.get("/api/usuarios/me", headers=auth)

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Maria Souza"


def test_editar_perfil_altera_somente_o_proprio_usuario(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com", nome="João Lima")

    cliente.patch("/api/usuarios/me", headers=auth_maria, json={"descricao": "Amo brechó"})

    assert cliente.get("/api/usuarios/me", headers=auth_maria).json()["descricao"] == "Amo brechó"
    assert cliente.get("/api/usuarios/me", headers=auth_joao).json()["descricao"] is None


def test_editar_para_email_de_outra_pessoa_falha(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    cadastrar_e_logar(cliente, "joao@email.com")

    resposta = cliente.patch("/api/usuarios/me", headers=auth_maria, json={"email": "joao@email.com"})
    assert resposta.status_code == 409


def test_categorias_fixas(cliente):
    nomes = [c["nome"] for c in cliente.get("/api/categorias").json()]
    assert nomes == ["Feminino", "Masculino", "Acessórios", "Calçados"]
