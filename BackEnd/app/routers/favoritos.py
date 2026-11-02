"""
Rotas dos favoritos do usuário logado.

Assim como no endereço, nenhuma rota recebe o id do usuário: os
favoritos são sempre os de quem está logado (identificado pelo token).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Favorito, Produto, Usuario
from app.schemas import FavoritoResposta, ProdutoPublico
from app.security import get_usuario_atual
from app.services.produtos import obter_produto

router = APIRouter(prefix="/favoritos", tags=["Favoritos"])


@router.get("", response_model=list[ProdutoPublico], summary="Listar meus favoritos")
def listar_favoritos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """
    Devolve os produtos favoritados, do mais recente para o mais antigo.
    Peças que foram vendidas continuam na lista (com status "vendido"),
    para a pessoa saber o que aconteceu com elas.
    """
    consulta = (
        select(Produto)
        .join(Favorito, Favorito.produto_id == Produto.id)
        .where(Favorito.usuario_id == usuario.id)
        .order_by(Favorito.criado_em.desc(), Favorito.id.desc())
    )
    return db.scalars(consulta).all()


@router.get("/ids", response_model=list[int], summary="Ids dos meus favoritos")
def ids_favoritos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """Lista leve, usada para pintar os corações nas páginas do catálogo."""
    return db.scalars(select(Favorito.produto_id).where(Favorito.usuario_id == usuario.id)).all()


@router.post(
    "/{produto_id}",
    response_model=FavoritoResposta,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar aos favoritos",
)
def adicionar_favorito(
    produto_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    produto = obter_produto(db, produto_id)  # 404 se não existir

    ja_existe = db.scalar(select(Favorito).where(
        Favorito.usuario_id == usuario.id, Favorito.produto_id == produto_id))
    if ja_existe:
        # Não cria duplicado: só confirma que já está nos favoritos
        return FavoritoResposta(produto_id=produto_id, favoritado=True)

    if produto.vendedor_id == usuario.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Você não pode favoritar o seu próprio anúncio.")
    if produto.status == "vendido":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta peça já foi vendida.")

    db.add(Favorito(usuario_id=usuario.id, produto_id=produto_id))
    try:
        db.commit()
    except IntegrityError:
        # Dois cliques ao mesmo tempo: o UNIQUE(usuario_id, produto_id) do banco
        # barra o segundo. O resultado final é o mesmo: está favoritado.
        db.rollback()
    return FavoritoResposta(produto_id=produto_id, favoritado=True)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remover dos favoritos")
def remover_favorito(
    produto_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    # Se não estava nos favoritos, não é erro: o resultado desejado
    # ("não está nos favoritos") já é verdadeiro.
    db.execute(delete(Favorito).where(
        Favorito.usuario_id == usuario.id, Favorito.produto_id == produto_id))
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Limpar todos os meus favoritos")
def limpar_favoritos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    db.execute(delete(Favorito).where(Favorito.usuario_id == usuario.id))
    db.commit()
