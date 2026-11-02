"""
Rotas do carrinho do usuário logado.

Todas as respostas trazem o carrinho completo já com os valores
calculados pelo servidor (ver services/carrinho.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ItemCarrinho, Usuario
from app.schemas import ResumoCarrinho
from app.security import get_usuario_atual
from app.services.carrinho import calcular_resumo
from app.services.produtos import obter_produto

router = APIRouter(prefix="/carrinho", tags=["Carrinho"])


@router.get("", response_model=ResumoCarrinho, summary="Ver meu carrinho")
def ver_carrinho(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    return calcular_resumo(db, usuario)


@router.post("/{produto_id}", response_model=ResumoCarrinho, summary="Adicionar peça ao carrinho")
def adicionar_ao_carrinho(
    produto_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Repare que só recebemos o ID da peça. O preço vem do banco,
    nunca do navegador.
    """
    produto = obter_produto(db, produto_id)  # 404 se não existir

    if produto.vendedor_id == usuario.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Você não pode comprar o seu próprio anúncio.")
    if produto.status != "disponivel":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta peça já foi vendida.")

    ja_esta = db.scalar(select(ItemCarrinho).where(
        ItemCarrinho.usuario_id == usuario.id, ItemCarrinho.produto_id == produto_id))
    if not ja_esta:  # peça única: não existe "quantidade 2"
        db.add(ItemCarrinho(usuario_id=usuario.id, produto_id=produto_id))
        try:
            db.commit()
        except IntegrityError:
            # Dois cliques ao mesmo tempo: o UNIQUE do banco barra o segundo
            db.rollback()

    return calcular_resumo(db, usuario)


@router.delete("/{produto_id}", response_model=ResumoCarrinho, summary="Remover peça do carrinho")
def remover_do_carrinho(
    produto_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    db.execute(delete(ItemCarrinho).where(
        ItemCarrinho.usuario_id == usuario.id, ItemCarrinho.produto_id == produto_id))
    db.commit()
    return calcular_resumo(db, usuario)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Esvaziar meu carrinho")
def esvaziar_carrinho(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    db.execute(delete(ItemCarrinho).where(ItemCarrinho.usuario_id == usuario.id))
    db.commit()
