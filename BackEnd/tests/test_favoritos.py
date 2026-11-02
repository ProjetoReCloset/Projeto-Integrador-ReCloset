"""
Testes dos favoritos.
"""
from app.database import SessionLocal
from app.models import Favorito
from tests.conftest import cadastrar_e_logar
from tests.test_produtos import DADOS, criar_produto, marcar_como_vendido


def preparar(cliente):
    """Maria anuncia 2 peças; João é quem favorita. Devolve (auth_joao, auth_maria, ids)."""
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com", nome="João Lima")
    ids = [criar_produto(cliente, auth_maria, dados={**DADOS, "nome": nome}).json()["id"]
           for nome in ("Blusa de tricô", "Calça jeans")]
    return auth_joao, auth_maria, ids


def test_favoritos_exigem_login(cliente):
    assert cliente.get("/api/favoritos").status_code == 401
    assert cliente.post("/api/favoritos/1").status_code == 401


def test_adicionar_e_listar(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    assert cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao).status_code == 201
    cliente.post(f"/api/favoritos/{calca}", headers=auth_joao)

    lista = cliente.get("/api/favoritos", headers=auth_joao).json()
    assert [p["nome"] for p in lista] == ["Calça jeans", "Blusa de tricô"]  # mais recente primeiro
    assert sorted(cliente.get("/api/favoritos/ids", headers=auth_joao).json()) == sorted([blusa, calca])


def test_favoritar_duas_vezes_nao_duplica(cliente):
    auth_joao, _, (blusa, _) = preparar(cliente)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    segunda = cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)

    assert segunda.json() == {"produto_id": blusa, "favoritado": True}
    with SessionLocal() as db:
        assert db.query(Favorito).count() == 1


def test_remover_favorito(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    cliente.post(f"/api/favoritos/{calca}", headers=auth_joao)

    assert cliente.delete(f"/api/favoritos/{blusa}", headers=auth_joao).status_code == 204
    assert cliente.get("/api/favoritos/ids", headers=auth_joao).json() == [calca]
    # Remover de novo não é erro
    assert cliente.delete(f"/api/favoritos/{blusa}", headers=auth_joao).status_code == 204


def test_limpar_so_apaga_os_meus(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    auth_ana = cadastrar_e_logar(cliente, "ana@email.com")
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_ana)

    assert cliente.delete("/api/favoritos", headers=auth_joao).status_code == 204
    assert cliente.get("/api/favoritos", headers=auth_joao).json() == []
    assert cliente.get("/api/favoritos/ids", headers=auth_ana).json() == [blusa]


def test_um_usuario_nao_ve_favoritos_do_outro(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    assert cliente.get("/api/favoritos", headers=auth_maria).json() == []


def test_produto_inexistente(cliente):
    auth_joao, _, _ = preparar(cliente)
    assert cliente.post("/api/favoritos/9999", headers=auth_joao).status_code == 404


def test_nao_favorita_o_proprio_anuncio(cliente):
    _, auth_maria, (blusa, _) = preparar(cliente)
    assert cliente.post(f"/api/favoritos/{blusa}", headers=auth_maria).status_code == 409


def test_nao_favorita_peca_vendida_mas_ela_continua_na_lista(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    marcar_como_vendido(blusa)
    marcar_como_vendido(calca)

    assert cliente.post(f"/api/favoritos/{calca}", headers=auth_joao).status_code == 409
    lista = cliente.get("/api/favoritos", headers=auth_joao).json()
    assert [(p["nome"], p["status"]) for p in lista] == [("Blusa de tricô", "vendido")]


def test_resumo_do_perfil_conta_favoritos(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/favoritos/{blusa}", headers=auth_joao)
    cliente.post(f"/api/favoritos/{calca}", headers=auth_joao)
    assert cliente.get("/api/usuarios/me/resumo", headers=auth_joao).json()["favoritos"] == 2
