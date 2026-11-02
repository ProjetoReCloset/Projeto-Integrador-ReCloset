"""
Testes do catálogo público: listagem, busca, filtro e ordenação.
"""
from tests.conftest import cadastrar_e_logar
from tests.test_produtos import DADOS, criar_produto, marcar_como_vendido


def popular(cliente):
    """Cria 4 anúncios variados e devolve o cabeçalho do vendedor."""
    auth = cadastrar_e_logar(cliente)
    pecas = [
        ("Blusa de tricô", "feminino", "45.00", "Blusa quentinha para o inverno."),
        ("Calça jeans", "feminino", "70.00", "Jeans azul, cintura alta e bem conservada."),
        ("Tênis branco", "calcados", "120.00", "Couro, pouco uso, combina com tudo."),
        ("Camisa social", "masculino", "38.50", "Algodão, ideal para o trabalho. Sem tricô."),
    ]
    for nome, categoria, preco, descricao in pecas:
        criar_produto(cliente, auth, dados={**DADOS, "nome": nome, "categoria": categoria,
                                            "preco": preco, "descricao": descricao})
    return auth


def nomes(resposta):
    return [p["nome"] for p in resposta.json()]


def test_catalogo_e_publico_e_lista_tudo(cliente):
    popular(cliente)
    resposta = cliente.get("/api/produtos")  # sem login
    assert resposta.status_code == 200
    assert len(resposta.json()) == 4


def test_catalogo_vazio(cliente):
    assert cliente.get("/api/produtos").json() == []


def test_mais_recentes_primeiro(cliente):
    popular(cliente)
    assert nomes(cliente.get("/api/produtos"))[0] == "Camisa social"


def test_peca_vendida_some_do_catalogo(cliente):
    auth = cadastrar_e_logar(cliente)
    vendida = criar_produto(cliente, auth, dados={**DADOS, "nome": "Já vendida"}).json()["id"]
    criar_produto(cliente, auth, dados={**DADOS, "nome": "Disponível"})
    marcar_como_vendido(vendida)

    assert nomes(cliente.get("/api/produtos")) == ["Disponível"]
    # mas a página de detalhes continua acessível (ex.: pelo histórico de pedidos)
    assert cliente.get(f"/api/produtos/{vendida}").json()["status"] == "vendido"


def test_busca_no_nome_e_na_descricao_sem_diferenciar_maiusculas(cliente):
    popular(cliente)
    # "TRICÔ" aparece no nome da blusa e na descrição da camisa
    assert sorted(nomes(cliente.get("/api/produtos", params={"busca": "TRICÔ"}))) == \
        ["Blusa de tricô", "Camisa social"]
    assert nomes(cliente.get("/api/produtos", params={"busca": "couro"})) == ["Tênis branco"]
    # sem acento também encontra
    assert "Blusa de tricô" in nomes(cliente.get("/api/produtos", params={"busca": "trico"}))
    assert cliente.get("/api/produtos", params={"busca": "inexistente"}).json() == []


def test_busca_com_caracteres_especiais_nao_vira_curinga(cliente):
    popular(cliente)
    # Em SQL, "%" significa "qualquer coisa". Aqui deve ser tratado como texto.
    assert cliente.get("/api/produtos", params={"busca": "%"}).json() == []


def test_filtro_por_categoria(cliente):
    popular(cliente)
    assert sorted(nomes(cliente.get("/api/produtos", params={"categoria": "feminino"}))) == \
        ["Blusa de tricô", "Calça jeans"]
    assert cliente.get("/api/produtos", params={"categoria": "acessorios"}).json() == []
    assert cliente.get("/api/produtos", params={"categoria": "eletronicos"}).status_code == 422


def test_ordenar_por_preco(cliente):
    popular(cliente)
    menor = [p["preco"] for p in cliente.get("/api/produtos", params={"ordem": "menor_preco"}).json()]
    maior = [p["preco"] for p in cliente.get("/api/produtos", params={"ordem": "maior_preco"}).json()]
    assert menor == ["38.50", "45.00", "70.00", "120.00"]
    assert maior == list(reversed(menor))


def test_busca_filtro_e_ordem_juntos(cliente):
    popular(cliente)
    resposta = cliente.get("/api/produtos", params={
        "categoria": "feminino", "busca": "a", "ordem": "maior_preco"})
    assert nomes(resposta) == ["Calça jeans", "Blusa de tricô"]


def test_limite_e_paginacao(cliente):
    popular(cliente)
    pagina1 = nomes(cliente.get("/api/produtos", params={"limite": 3, "pagina": 1}))
    pagina2 = nomes(cliente.get("/api/produtos", params={"limite": 3, "pagina": 2}))
    assert len(pagina1) == 3 and len(pagina2) == 1
    assert not set(pagina1) & set(pagina2)  # nenhuma peça repetida entre as páginas


def test_busca_acompanha_a_edicao_do_anuncio(cliente):
    auth = cadastrar_e_logar(cliente)
    produto_id = criar_produto(cliente, auth).json()["id"]
    cliente.put(f"/api/produtos/{produto_id}", headers=auth,
                json={**DADOS, "nome": "Jaqueta de couro"})

    assert nomes(cliente.get("/api/produtos", params={"busca": "jaqueta"})) == ["Jaqueta de couro"]
    assert cliente.get("/api/produtos", params={"busca": "blusa"}).json() == []
