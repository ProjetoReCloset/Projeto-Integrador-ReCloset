"""
Testes do carrinho: totais calculados no servidor e regras de peça única.
"""
from app.database import SessionLocal
from app.models import ItemCarrinho
from tests.conftest import cadastrar_e_logar
from tests.test_produtos import DADOS, criar_produto, marcar_como_vendido


def preparar(cliente):
    """Maria vende 2 peças (45,90 e 70,00); João compra. Devolve (auth_joao, auth_maria, ids)."""
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com", nome="João Lima")
    blusa = criar_produto(cliente, auth_maria, dados={**DADOS, "nome": "Blusa", "preco": "45.90"}).json()["id"]
    calca = criar_produto(cliente, auth_maria, dados={**DADOS, "nome": "Calça", "preco": "70.00"}).json()["id"]
    return auth_joao, auth_maria, (blusa, calca)


def test_carrinho_exige_login(cliente):
    assert cliente.get("/api/carrinho").status_code == 401
    assert cliente.post("/api/carrinho/1").status_code == 401


def test_carrinho_vazio(cliente):
    auth = cadastrar_e_logar(cliente)
    resumo = cliente.get("/api/carrinho", headers=auth).json()
    assert resumo == {"itens": [], "quantidade": 0, "subtotal": "0.00",
                      "valor_entrega": "0.00", "total": "0.00", "pode_finalizar": False}


def test_totais_calculados_pelo_servidor(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    resumo = cliente.post(f"/api/carrinho/{calca}", headers=auth_joao).json()

    assert resumo["quantidade"] == 2
    assert resumo["subtotal"] == "115.90"
    assert resumo["valor_entrega"] == "15.00"   # valor do .env (padrão 15,00)
    assert resumo["total"] == "130.90"
    assert resumo["pode_finalizar"] is True


def test_preco_enviado_pelo_navegador_e_ignorado(cliente):
    auth_joao, _, (blusa, _) = preparar(cliente)
    # Tentativa de "trapaça": mandar um preço menor junto
    resumo = cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao,
                          json={"preco": "1.00", "total": "1.00"}).json()
    assert resumo["subtotal"] == "45.90"


def test_preco_acompanha_o_banco(cliente):
    """Se o vendedor muda o preço, o carrinho mostra o valor novo."""
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    cliente.put(f"/api/produtos/{blusa}", headers=auth_maria, json={**DADOS, "preco": "39.90"})

    assert cliente.get("/api/carrinho", headers=auth_joao).json()["subtotal"] == "39.90"


def test_mesma_peca_duas_vezes_nao_duplica(cliente):
    auth_joao, _, (blusa, _) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    resumo = cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao).json()

    assert resumo["quantidade"] == 1 and resumo["subtotal"] == "45.90"
    with SessionLocal() as db:
        assert db.query(ItemCarrinho).count() == 1


def test_remover_e_esvaziar(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    cliente.post(f"/api/carrinho/{calca}", headers=auth_joao)

    resumo = cliente.delete(f"/api/carrinho/{blusa}", headers=auth_joao).json()
    assert [i["produto"]["nome"] for i in resumo["itens"]] == ["Calça"]
    assert resumo["total"] == "85.00"

    assert cliente.delete("/api/carrinho", headers=auth_joao).status_code == 204
    assert cliente.get("/api/carrinho", headers=auth_joao).json()["itens"] == []


def test_carrinhos_sao_separados(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    auth_ana = cadastrar_e_logar(cliente, "ana@email.com")
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)

    assert cliente.get("/api/carrinho", headers=auth_ana).json()["itens"] == []
    cliente.delete("/api/carrinho", headers=auth_ana)  # esvaziar o da Ana não afeta o do João
    assert cliente.get("/api/carrinho", headers=auth_joao).json()["quantidade"] == 1


def test_nao_compra_o_proprio_anuncio(cliente):
    _, auth_maria, (blusa, _) = preparar(cliente)
    assert cliente.post(f"/api/carrinho/{blusa}", headers=auth_maria).status_code == 409


def test_nao_adiciona_peca_vendida_ou_inexistente(cliente):
    auth_joao, _, (blusa, _) = preparar(cliente)
    marcar_como_vendido(blusa)
    assert cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao).status_code == 409
    assert cliente.post("/api/carrinho/9999", headers=auth_joao).status_code == 404


def test_peca_vendida_depois_fica_marcada_e_sai_da_conta(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    cliente.post(f"/api/carrinho/{calca}", headers=auth_joao)
    marcar_como_vendido(blusa)  # outra pessoa comprou a blusa

    resumo = cliente.get("/api/carrinho", headers=auth_joao).json()
    disponibilidade = {i["produto"]["nome"]: i["disponivel"] for i in resumo["itens"]}
    assert disponibilidade == {"Blusa": False, "Calça": True}
    assert resumo["subtotal"] == "70.00" and resumo["total"] == "85.00"
    assert resumo["pode_finalizar"] is False  # precisa remover a peça vendida antes

    resumo = cliente.delete(f"/api/carrinho/{blusa}", headers=auth_joao).json()
    assert resumo["pode_finalizar"] is True


def test_excluir_anuncio_tira_do_carrinho(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    cliente.delete(f"/api/produtos/{blusa}", headers=auth_maria)

    assert cliente.get("/api/carrinho", headers=auth_joao).json()["itens"] == []
