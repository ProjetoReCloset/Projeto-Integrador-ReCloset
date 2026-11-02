"""
Rotas dos anúncios (produtos).

Neste arquivo: catálogo público (com busca, filtro e ordenação),
cadastrar, ver, listar os meus, editar, excluir e gerenciar as fotos.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Categoria, ImagemProduto, Produto, Usuario
from app.schemas import CategoriaSlug, ProdutoEntrada, ProdutoPublico
from app.security import get_usuario_atual
from app.services.produtos import (
    MAX_IMAGENS,
    atualizar_texto_busca,
    normalizar,
    obter_categoria,
    obter_produto,
    obter_produto_do_vendedor,
)
from app.services.uploads import apagar_imagem, salvar_imagem

router = APIRouter(prefix="/produtos", tags=["Anúncios"])


async def _salvar_varias(arquivos: list[UploadFile]) -> list[str]:
    """
    Salva várias fotos. Se uma delas for inválida, apaga as que já
    tinham sido salvas, para não deixar arquivos "órfãos" na pasta.
    """
    salvas = []
    try:
        for arquivo in arquivos:
            salvas.append(await salvar_imagem(arquivo, "produtos"))
    except HTTPException:
        for caminho in salvas:
            apagar_imagem(caminho)
        raise
    return salvas


@router.post(
    "",
    response_model=ProdutoPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar um anúncio (com fotos)",
)
async def cadastrar_produto(
    # Form(): os dados chegam como formulário (multipart), porque junto vão os arquivos
    nome: Annotated[str, Form()],
    descricao: Annotated[str, Form(description="Inclua o estado de conservação da peça")],
    preco: Annotated[str, Form(description="Ex.: 45.90")],
    categoria: Annotated[str, Form(description="feminino, masculino, acessorios ou calcados")],
    tamanho: Annotated[str | None, Form()] = None,
    imagens: list[UploadFile] = File(description=f"De 1 a {MAX_IMAGENS} fotos (JPG, PNG ou WEBP)"),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    # As regras de cada campo ficam num lugar só: o schema ProdutoEntrada
    # (o mesmo usado na edição). Se algo estiver errado, respondemos 422.
    try:
        dados = ProdutoEntrada(nome=nome, descricao=descricao, preco=preco,
                               categoria=categoria, tamanho=tamanho)
    except ValidationError as erro:
        raise RequestValidationError(erro.errors())

    if not 1 <= len(imagens) <= MAX_IMAGENS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Envie de 1 a {MAX_IMAGENS} fotos da peça.")

    categoria = obter_categoria(db, dados.categoria)
    caminhos = await _salvar_varias(imagens)

    produto = Produto(
        vendedor_id=usuario.id,
        categoria_id=categoria.id,
        nome=dados.nome,
        descricao=dados.descricao,
        tamanho=dados.tamanho,
        preco=dados.preco,
        status="disponivel",  # toda peça nova começa disponível
        imagens=[ImagemProduto(caminho=c, ordem=i) for i, c in enumerate(caminhos)],
    )
    atualizar_texto_busca(produto)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@router.get("", response_model=list[ProdutoPublico], summary="Catálogo: listar peças disponíveis")
def listar_produtos(
    busca: Annotated[str | None, Query(max_length=100, description="Procura no nome e na descrição")] = None,
    categoria: Annotated[CategoriaSlug | None, Query()] = None,
    ordem: Annotated[Literal["recentes", "menor_preco", "maior_preco"], Query()] = "recentes",
    limite: Annotated[int, Query(ge=1, le=100)] = 60,
    pagina: Annotated[int, Query(ge=1)] = 1,
    db: Session = Depends(get_db),
):
    """
    Rota pública (não precisa de login). Mostra SÓ as peças disponíveis:
    uma peça vendida não aparece mais no catálogo.
    """
    consulta = select(Produto).where(Produto.status == "disponivel")

    if busca and busca.strip():
        # O termo é normalizado do mesmo jeito que o texto_busca do produto
        # (sem acento e minúsculo): "TRICÔ" vira "trico".
        termo = normalizar(busca.strip())
        # contains() gera "LIKE '%termo%'". autoescape=True faz com que
        # % e _ digitados pelo usuário sejam tratados como texto comum.
        consulta = consulta.where(Produto.texto_busca.contains(termo, autoescape=True))

    if categoria:
        consulta = consulta.join(Produto.categoria).where(Categoria.slug == categoria)

    if ordem == "menor_preco":
        consulta = consulta.order_by(Produto.preco.asc(), Produto.id.desc())
    elif ordem == "maior_preco":
        consulta = consulta.order_by(Produto.preco.desc(), Produto.id.desc())
    else:
        consulta = consulta.order_by(Produto.criado_em.desc(), Produto.id.desc())

    # Paginação simples: pula as páginas anteriores e pega "limite" itens
    consulta = consulta.offset((pagina - 1) * limite).limit(limite)
    return db.scalars(consulta).all()


# Atenção: esta rota precisa vir ANTES de "/{produto_id}".
# Senão o FastAPI tentaria entender "meus" como um id.
@router.get("/meus", response_model=list[ProdutoPublico], summary="Listar meus anúncios")
def listar_meus_produtos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    consulta = (
        select(Produto)
        .where(Produto.vendedor_id == usuario.id)
        .order_by(Produto.criado_em.desc())
    )
    return db.scalars(consulta).all()


@router.get("/{produto_id}", response_model=ProdutoPublico, summary="Ver um anúncio")
def ver_produto(produto_id: int, db: Session = Depends(get_db)):
    # Rota pública: qualquer pessoa pode ver os detalhes de uma peça
    return obter_produto(db, produto_id)


@router.put("/{produto_id}", response_model=ProdutoPublico, summary="Editar um anúncio")
def editar_produto(
    produto_id: int,
    dados: ProdutoEntrada,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    produto = obter_produto_do_vendedor(db, produto_id, usuario)  # 404 / 403 / 409

    produto.nome = dados.nome
    produto.descricao = dados.descricao
    produto.tamanho = dados.tamanho
    produto.preco = dados.preco
    produto.categoria_id = obter_categoria(db, dados.categoria).id
    atualizar_texto_busca(produto)

    db.commit()
    db.refresh(produto)
    return produto


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir um anúncio")
def excluir_produto(
    produto_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    # Peças vendidas não podem ser excluídas: fazem parte do histórico de pedidos
    produto = obter_produto_do_vendedor(db, produto_id, usuario)
    caminhos = [imagem.caminho for imagem in produto.imagens]

    # O banco remove junto (ON DELETE CASCADE) os favoritos e os itens
    # de carrinho que apontavam para esta peça.
    db.delete(produto)
    db.commit()

    for caminho in caminhos:  # os arquivos só são apagados depois do commit
        apagar_imagem(caminho)


@router.post("/{produto_id}/imagens", response_model=ProdutoPublico, summary="Adicionar fotos")
async def adicionar_imagens(
    produto_id: int,
    imagens: list[UploadFile] = File(),
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    produto = obter_produto_do_vendedor(db, produto_id, usuario)

    if len(produto.imagens) + len(imagens) > MAX_IMAGENS:
        livres = MAX_IMAGENS - len(produto.imagens)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Cada anúncio pode ter até {MAX_IMAGENS} fotos. Você ainda pode enviar {livres}.",
        )

    proxima_ordem = max((imagem.ordem for imagem in produto.imagens), default=-1) + 1
    for i, caminho in enumerate(await _salvar_varias(imagens)):
        produto.imagens.append(ImagemProduto(caminho=caminho, ordem=proxima_ordem + i))

    db.commit()
    db.refresh(produto)
    return produto


@router.delete(
    "/{produto_id}/imagens/{imagem_id}",
    response_model=ProdutoPublico,
    summary="Remover uma foto",
)
def remover_imagem(
    produto_id: int,
    imagem_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    produto = obter_produto_do_vendedor(db, produto_id, usuario)

    # A foto precisa ser DESTE produto (evita apagar foto de outro anúncio)
    imagem = next((img for img in produto.imagens if img.id == imagem_id), None)
    if imagem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto não encontrada neste anúncio.")
    if len(produto.imagens) == 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "O anúncio precisa ter pelo menos uma foto.")

    caminho = imagem.caminho
    produto.imagens.remove(imagem)  # delete-orphan: o registro é apagado do banco
    db.commit()
    apagar_imagem(caminho)

    db.refresh(produto)
    return produto
