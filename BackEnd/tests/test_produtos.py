"""
Testes dos anúncios: cadastro com fotos, edição, exclusão e regras.
"""
from app.database import SessionLocal
from app.models import Favorito, ItemCarrinho, Produto
from tests.conftest import cadastrar_e_logar
from tests.test_perfil_endereco import PNG_1PX

DADOS = {
    "nome": "Blusa de tricô",
    "descricao": "Usada poucas vezes, sem furos nem manchas.",
    "tamanho": "M",
    "preco": "45.90",
    "categoria": "feminino",
}


def foto(nome="foto.png"):
    return ("imagens", (nome, PNG_1PX, "image/png"))


def criar_produto(cliente, auth, dados=None, n_fotos=1):
    return cliente.post("/api/produtos", headers=auth, data=dados or DADOS,
                        files=[foto(f"f{i}.png") for i in range(n_fotos)])


def marcar_como_vendido(produto_id):
    """Simula uma venda (o checkout será feito numa etapa futura)."""
    with SessionLocal() as db:
        db.get(Produto, produto_id).status = "vendido"
        db.commit()


# ---------- Cadastro ----------

def test_cadastrar_anuncio_com_fotos(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = criar_produto(cliente, auth, n_fotos=2)

    assert resposta.status_code == 201
    produto = resposta.json()
    assert produto["status"] == "disponivel"
    assert produto["preco"] == "45.90"
    assert produto["categoria"]["nome"] == "Feminino"
    assert produto["vendedor"]["nome"] == "Maria Souza"
    assert "email" not in produto["vendedor"]  # dados privados do vendedor não aparecem
    assert len(produto["imagens"]) == 2


def test_anuncio_exige_login(cliente):
    resposta = cliente.post("/api/produtos", data=DADOS, files=[foto()])
    assert resposta.status_code == 401


def test_anuncio_sem_foto_e_recusado(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.post("/api/produtos", headers=auth, data=DADOS)
    assert resposta.status_code == 422


def test_anuncio_com_fotos_demais_e_recusado(cliente):
    auth = cadastrar_e_logar(cliente)
    assert criar_produto(cliente, auth, n_fotos=6).status_code == 422


def test_anuncio_com_arquivo_que_nao_e_imagem(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.post("/api/produtos", headers=auth, data=DADOS,
                            files=[("imagens", ("x.jpg", b"nao sou imagem", "image/jpeg"))])
    assert resposta.status_code == 415


def test_validacao_dos_campos_do_anuncio(cliente):
    auth = cadastrar_e_logar(cliente)
    invalido = {**DADOS, "nome": "ab", "preco": "0", "categoria": "eletronicos"}
    resposta = criar_produto(cliente, auth, dados=invalido)

    assert resposta.status_code == 422
    for campo in ("Nome", "Preço", "Categoria"):
        assert campo in resposta.json()["detail"]


def test_preco_com_mais_de_duas_casas_e_recusado(cliente):
    auth = cadastrar_e_logar(cliente)
    assert criar_produto(cliente, auth, dados={**DADOS, "preco": "10.999"}).status_code == 422


# ---------- Ver e listar ----------

def test_ver_anuncio_e_publico(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_id = criar_produto(cliente, auth).json()["id"]

    resposta = cliente.get(f"/api/produtos/{produto_id}")  # sem token
    assert resposta.status_code == 200
    assert cliente.get("/api/produtos/9999").status_code == 404


def test_meus_anuncios_lista_so_os_meus(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com")
    criar_produto(cliente, auth_maria)
    criar_produto(cliente, auth_maria, dados={**DADOS, "nome": "Calça jeans"})
    criar_produto(cliente, auth_joao, dados={**DADOS, "nome": "Tênis do João"})

    nomes = [p["nome"] for p in cliente.get("/api/produtos/meus", headers=auth_maria).json()]
    assert sorted(nomes) == ["Blusa de tricô", "Calça jeans"]


def test_resumo_do_perfil_conta_anuncios_e_vendas(cliente):
    auth = cadastrar_e_logar(cliente)
    primeiro = criar_produto(cliente, auth).json()["id"]
    criar_produto(cliente, auth)
    marcar_como_vendido(primeiro)

    resumo = cliente.get("/api/usuarios/me/resumo", headers=auth).json()
    assert resumo["produtos"] == 2 and resumo["vendas"] == 1


# ---------- Editar ----------

def test_dono_edita_anuncio(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_id = criar_produto(cliente, auth).json()["id"]

    resposta = cliente.put(f"/api/produtos/{produto_id}", headers=auth,
                           json={**DADOS, "preco": "39.90", "categoria": "acessorios"})
    assert resposta.status_code == 200
    assert resposta.json()["preco"] == "39.90"
    assert resposta.json()["categoria"]["slug"] == "acessorios"


def test_outra_pessoa_nao_edita_nem_exclui(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com")
    produto_id = criar_produto(cliente, auth_maria).json()["id"]

    assert cliente.put(f"/api/produtos/{produto_id}", headers=auth_joao,
                       json={**DADOS, "preco": "1.00"}).status_code == 403
    assert cliente.delete(f"/api/produtos/{produto_id}", headers=auth_joao).status_code == 403
    assert cliente.post(f"/api/produtos/{produto_id}/imagens", headers=auth_joao,
                        files=[foto()]).status_code == 403
    # O preço continua o original
    assert cliente.get(f"/api/produtos/{produto_id}").json()["preco"] == "45.90"


def test_peca_vendida_nao_pode_ser_editada_nem_excluida(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_id = criar_produto(cliente, auth).json()["id"]
    marcar_como_vendido(produto_id)

    assert cliente.put(f"/api/produtos/{produto_id}", headers=auth, json=DADOS).status_code == 409
    assert cliente.delete(f"/api/produtos/{produto_id}", headers=auth).status_code == 409


# ---------- Fotos ----------

def test_adicionar_e_remover_fotos(cliente):
    auth = cadastrar_e_logar(cliente)
    produto = criar_produto(cliente, auth).json()

    produto = cliente.post(f"/api/produtos/{produto['id']}/imagens", headers=auth,
                           files=[foto(), foto()]).json()
    assert len(produto["imagens"]) == 3

    imagem = produto["imagens"][0]
    resposta = cliente.delete(f"/api/produtos/{produto['id']}/imagens/{imagem['id']}", headers=auth)
    assert len(resposta.json()["imagens"]) == 2
    assert cliente.get(f"/uploads/{imagem['caminho']}").status_code == 404  # arquivo apagado


def test_nao_passa_do_limite_de_fotos(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_id = criar_produto(cliente, auth, n_fotos=4).json()["id"]

    resposta = cliente.post(f"/api/produtos/{produto_id}/imagens", headers=auth, files=[foto(), foto()])
    assert resposta.status_code == 422


def test_nao_remove_a_ultima_foto(cliente):
    auth = cadastrar_e_logar(cliente)
    produto = criar_produto(cliente, auth).json()
    imagem_id = produto["imagens"][0]["id"]

    resposta = cliente.delete(f"/api/produtos/{produto['id']}/imagens/{imagem_id}", headers=auth)
    assert resposta.status_code == 409


def test_nao_remove_foto_de_outro_anuncio(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_a = criar_produto(cliente, auth, n_fotos=2).json()
    produto_b = criar_produto(cliente, auth, n_fotos=2).json()
    foto_do_b = produto_b["imagens"][0]["id"]

    resposta = cliente.delete(f"/api/produtos/{produto_a['id']}/imagens/{foto_do_b}", headers=auth)
    assert resposta.status_code == 404


# ---------- Excluir ----------

def test_excluir_anuncio_remove_fotos_favoritos_e_carrinho(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com")
    produto = criar_produto(cliente, auth_maria).json()
    joao_id = cliente.get("/api/usuarios/me", headers=auth_joao).json()["id"]

    # João favoritou e colocou no carrinho (direto no banco: essas rotas vêm depois)
    with SessionLocal() as db:
        db.add(Favorito(usuario_id=joao_id, produto_id=produto["id"]))
        db.add(ItemCarrinho(usuario_id=joao_id, produto_id=produto["id"]))
        db.commit()

    assert cliente.delete(f"/api/produtos/{produto['id']}", headers=auth_maria).status_code == 204
    assert cliente.get(f"/api/produtos/{produto['id']}").status_code == 404
    assert cliente.get(f"/uploads/{produto['imagens'][0]['caminho']}").status_code == 404
    with SessionLocal() as db:
        assert db.query(Favorito).count() == 0
        assert db.query(ItemCarrinho).count() == 0
