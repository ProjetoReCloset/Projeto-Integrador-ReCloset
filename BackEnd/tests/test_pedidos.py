"""
Testes da finalização da compra e dos pedidos.
"""
import threading

from app.database import SessionLocal
from app.models import ItemCarrinho, ItemPedido, Pedido, Produto
from tests.conftest import cadastrar_e_logar
from tests.test_perfil_endereco import ENDERECO
from tests.test_produtos import DADOS, criar_produto


def comprador(cliente, email="joao@email.com", com_endereco=True):
    auth = cadastrar_e_logar(cliente, email, nome="Comprador")
    if com_endereco:
        cliente.put("/api/endereco", headers=auth, json=ENDERECO)
    return auth


def preparar(cliente):
    """Maria vende blusa (45,90) e calça (70,00). João tem as duas no carrinho."""
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    blusa = criar_produto(cliente, auth_maria, dados={**DADOS, "nome": "Blusa", "preco": "45.90"}).json()["id"]
    calca = criar_produto(cliente, auth_maria, dados={**DADOS, "nome": "Calça", "preco": "70.00"}).json()["id"]
    auth_joao = comprador(cliente)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)
    cliente.post(f"/api/carrinho/{calca}", headers=auth_joao)
    return auth_joao, auth_maria, (blusa, calca)


def status_do_produto(produto_id):
    with SessionLocal() as db:
        return db.get(Produto, produto_id).status


# ---------- Compra que dá certo ----------

def test_finalizar_compra(cliente):
    auth_joao, _, (blusa, calca) = preparar(cliente)
    resposta = cliente.post("/api/pedidos", headers=auth_joao, json={})

    assert resposta.status_code == 201
    pedido = resposta.json()
    assert pedido["status"] == "confirmado"
    assert pedido["subtotal"] == "115.90"
    assert pedido["valor_entrega"] == "15.00"
    assert pedido["total"] == "130.90"
    assert sorted(i["produto"]["nome"] for i in pedido["itens"]) == ["Blusa", "Calça"]
    assert "Rua Exemplo, 123" in pedido["endereco_entrega"]


def test_compra_marca_pecas_como_vendidas_e_limpa_o_carrinho(cliente):
    auth_joao, auth_maria, (blusa, calca) = preparar(cliente)
    cliente.post("/api/pedidos", headers=auth_joao, json={})

    assert status_do_produto(blusa) == "vendido" and status_do_produto(calca) == "vendido"
    assert cliente.get("/api/carrinho", headers=auth_joao).json()["itens"] == []
    assert cliente.get("/api/produtos").json() == []  # sumiram do catálogo
    # e a vendedora vê as vendas no resumo do perfil
    assert cliente.get("/api/usuarios/me/resumo", headers=auth_maria).json()["vendas"] == 2


def test_total_confirmado_igual_passa_e_diferente_bloqueia(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    # O vendedor muda o preço enquanto o João revisa o pedido
    cliente.put(f"/api/produtos/{blusa}", headers=auth_maria, json={**DADOS, "nome": "Blusa", "preco": "50.00"})

    resposta = cliente.post("/api/pedidos", headers=auth_joao, json={"total_confirmado": "130.90"})
    assert resposta.status_code == 409
    assert status_do_produto(blusa) == "disponivel"  # nada foi gravado (rollback)

    resposta = cliente.post("/api/pedidos", headers=auth_joao, json={"total_confirmado": "135.00"})
    assert resposta.status_code == 201


def test_preco_do_pedido_nao_muda_depois(cliente):
    auth_joao, _, _ = preparar(cliente)
    pedido_id = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()["id"]
    with SessionLocal() as db:
        for item in db.query(ItemPedido).all():
            item.produto.preco = 1  # mesmo que o preço do produto mude no banco...
        db.commit()

    pedido = cliente.get(f"/api/pedidos/{pedido_id}", headers=auth_joao).json()
    assert pedido["total"] == "130.90"  # ...o pedido guarda os valores da hora da compra
    assert sorted(i["preco"] for i in pedido["itens"]) == ["45.90", "70.00"]


def test_endereco_do_pedido_e_uma_copia(cliente):
    auth_joao, _, _ = preparar(cliente)
    pedido_id = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()["id"]
    cliente.put("/api/endereco", headers=auth_joao, json={**ENDERECO, "rua": "Rua Nova"})
    cliente.delete("/api/endereco", headers=auth_joao)

    pedido = cliente.get(f"/api/pedidos/{pedido_id}", headers=auth_joao).json()
    assert "Rua Exemplo" in pedido["endereco_entrega"]


# ---------- Compras que NÃO podem acontecer ----------

def test_sem_endereco_nao_finaliza(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    blusa = criar_produto(cliente, auth_maria).json()["id"]
    auth_joao = comprador(cliente, com_endereco=False)
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_joao)

    resposta = cliente.post("/api/pedidos", headers=auth_joao, json={})
    assert resposta.status_code == 409 and "endereço" in resposta.json()["detail"]
    assert status_do_produto(blusa) == "disponivel"


def test_carrinho_vazio_nao_finaliza(cliente):
    auth = comprador(cliente)
    assert cliente.post("/api/pedidos", headers=auth, json={}).status_code == 409


def test_peca_ja_vendida_nao_e_vendida_de_novo(cliente):
    auth_joao, auth_maria, (blusa, calca) = preparar(cliente)
    auth_ana = comprador(cliente, "ana@email.com")
    cliente.post(f"/api/carrinho/{blusa}", headers=auth_ana)

    assert cliente.post("/api/pedidos", headers=auth_ana, json={}).status_code == 201
    # João ainda tem a blusa (já vendida) no carrinho
    resposta = cliente.post("/api/pedidos", headers=auth_joao, json={})
    assert resposta.status_code == 409 and "Blusa" in resposta.json()["detail"]
    # Nada da compra do João foi gravado: a calça continua disponível
    assert status_do_produto(calca) == "disponivel"
    with SessionLocal() as db:
        assert db.query(Pedido).count() == 1
        assert db.query(ItemPedido).filter_by(produto_id=blusa).count() == 1


def test_duas_compras_ao_mesmo_tempo_so_uma_passa(cliente):
    """
    Ana e Bruno clicam em "Confirmar" no MESMO instante, com a mesma peça.
    Usamos duas threads e uma "barreira" para que as duas requisições
    saiam juntas. Só uma pode virar pedido.
    """
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    blusa = criar_produto(cliente, auth_maria).json()["id"]
    compradores = [comprador(cliente, f"pessoa{i}@email.com") for i in range(2)]
    for auth in compradores:
        cliente.post(f"/api/carrinho/{blusa}", headers=auth)

    barreira = threading.Barrier(len(compradores))
    resultados = []

    def comprar(auth):
        barreira.wait()  # espera a outra thread ficar pronta, e as duas seguem juntas
        resultados.append(cliente.post("/api/pedidos", headers=auth, json={}).status_code)

    threads = [threading.Thread(target=comprar, args=(auth,)) for auth in compradores]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(resultados) == [201, 409]
    with SessionLocal() as db:
        assert db.query(Pedido).count() == 1
        assert db.query(ItemPedido).filter_by(produto_id=blusa).count() == 1


def test_peca_vendida_bem_no_meio_da_compra_desfaz_tudo(cliente):
    """
    O caso mais difícil: as verificações iniciais passaram, mas no instante
    seguinte outra pessoa compra uma das peças. Simulamos isso com um
    "gancho" que roda logo antes do primeiro UPDATE do pedido do João e,
    por OUTRA conexão, vende a calça.
    Resultado esperado: o UPDATE condicional da calça afeta 0 linhas, o
    rollback devolve a blusa para "disponível" e nenhum pedido é criado.
    """
    from sqlalchemy import event, text
    from app.database import engine

    auth_joao, _, (blusa, calca) = preparar(cliente)
    ja_rodou = []

    def vender_calca_por_fora(conn, cursor, sql, *args):
        if not ja_rodou and sql.startswith("UPDATE produto SET status"):
            ja_rodou.append(True)
            with engine.connect() as outra:  # outra conexão = outra pessoa
                outra.execute(text("UPDATE produto SET status='vendido' WHERE id=:id"), {"id": calca})
                outra.commit()

    event.listen(engine, "before_cursor_execute", vender_calca_por_fora)
    try:
        resposta = cliente.post("/api/pedidos", headers=auth_joao, json={})
    finally:
        event.remove(engine, "before_cursor_execute", vender_calca_por_fora)

    assert ja_rodou  # o gancho realmente rodou
    assert resposta.status_code == 409 and "acabou de ser vendida" in resposta.json()["detail"]
    assert status_do_produto(blusa) == "disponivel"  # rollback desfez a blusa
    with SessionLocal() as db:
        assert db.query(Pedido).count() == 0
        assert db.query(ItemCarrinho).filter_by(produto_id=blusa).count() == 1


def test_compra_parcial_nao_existe(cliente):
    """Se UMA peça já estava vendida, NENHUMA é vendida (tudo ou nada)."""
    auth_joao, _, (blusa, calca) = preparar(cliente)
    # Simula a calça sendo vendida no meio do caminho (depois das verificações)
    with SessionLocal() as db:
        db.get(Produto, calca).status = "vendido"
        db.commit()

    assert cliente.post("/api/pedidos", headers=auth_joao, json={}).status_code == 409
    assert status_do_produto(blusa) == "disponivel"
    with SessionLocal() as db:
        assert db.query(Pedido).count() == 0
        assert db.query(ItemCarrinho).count() == 2  # o carrinho continua como estava


def test_banco_recusa_a_mesma_peca_em_dois_itens(cliente):
    """A segunda barreira (UNIQUE em item_pedido.produto_id) funciona sozinha."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    auth_joao, _, (blusa, _) = preparar(cliente)
    pedido_id = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()["id"]
    with SessionLocal() as db:
        db.add(ItemPedido(pedido_id=pedido_id, produto_id=blusa, preco=1))
        with pytest.raises(IntegrityError):
            db.commit()


# ---------- Consultar pedidos ----------

def test_listar_e_ver_meus_pedidos(cliente):
    auth_joao, _, _ = preparar(cliente)
    pedido_id = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()["id"]

    lista = cliente.get("/api/pedidos", headers=auth_joao).json()
    assert [p["id"] for p in lista] == [pedido_id]
    assert cliente.get(f"/api/pedidos/{pedido_id}", headers=auth_joao).status_code == 200


def test_nao_ve_pedido_de_outra_pessoa(cliente):
    auth_joao, auth_maria, _ = preparar(cliente)
    pedido_id = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()["id"]

    assert cliente.get(f"/api/pedidos/{pedido_id}", headers=auth_maria).status_code == 404
    assert cliente.get("/api/pedidos", headers=auth_maria).json() == []
    assert cliente.get("/api/pedidos").status_code == 401


def test_peca_vendida_nao_pode_mais_ser_alterada_pelo_vendedor(cliente):
    auth_joao, auth_maria, (blusa, _) = preparar(cliente)
    cliente.post("/api/pedidos", headers=auth_joao, json={})

    assert cliente.put(f"/api/produtos/{blusa}", headers=auth_maria, json=DADOS).status_code == 409
    assert cliente.delete(f"/api/produtos/{blusa}", headers=auth_maria).status_code == 409


def test_datas_saem_com_fuso_utc(cliente):
    """Sem o fuso, o navegador no Brasil mostraria o dia errado à noite."""
    auth_joao, _, _ = preparar(cliente)
    pedido = cliente.post("/api/pedidos", headers=auth_joao, json={}).json()
    produto = cliente.get(f"/api/produtos/{pedido['itens'][0]['produto_id']}").json()

    for data in (pedido["criado_em"], produto["criado_em"]):
        assert data.endswith("Z") or data.endswith("+00:00")
