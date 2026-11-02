"""
Regras de negócio dos anúncios.

Ficam aqui (e não dentro das rotas) porque serão usadas em vários
lugares: anúncios, carrinho e pedidos.
"""
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Categoria, Produto, Usuario

MAX_IMAGENS = 5  # fotos por anúncio


def normalizar(texto: str) -> str:
    """
    "Blusa de TRICÔ" -> "blusa de trico"

    unicodedata.normalize("NFKD") separa cada letra do seu acento
    ("ô" vira "o" + "^"); depois jogamos fora os acentos.
    """
    separado = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in separado if not unicodedata.combining(c))
    return sem_acento.casefold()


def atualizar_texto_busca(produto: Produto) -> None:
    """Chamar sempre que o nome ou a descrição mudarem."""
    produto.texto_busca = normalizar(f"{produto.nome} {produto.descricao}")


def obter_produto(db: Session, produto_id: int) -> Produto:
    """Busca o produto ou responde 404."""
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anúncio não encontrado.")
    return produto


def obter_produto_do_vendedor(db: Session, produto_id: int, usuario: Usuario) -> Produto:
    """
    Busca um produto que o usuário quer ALTERAR.
    - 404 se não existir
    - 403 se for de outra pessoa
    - 409 se já foi vendido (o anúncio vira histórico e não muda mais)
    """
    produto = obter_produto(db, produto_id)
    if produto.vendedor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Você só pode alterar os seus próprios anúncios.")
    if produto.status == "vendido":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta peça já foi vendida e não pode ser alterada.")
    return produto


def obter_categoria(db: Session, slug: str) -> Categoria:
    categoria = db.scalar(select(Categoria).where(Categoria.slug == slug))
    if categoria is None:  # não deve acontecer: o schema só aceita as 4 categorias
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Categoria inválida.")
    return categoria
