"""
Rotas dos pedidos do usuário logado.

A regra da compra (transação, peça única etc.) está em services/pedidos.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pedido, Usuario
from app.schemas import PedidoEntrada, PedidoPublico
from app.security import get_usuario_atual
from app.services.pedidos import finalizar_compra

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post(
    "",
    response_model=PedidoPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Finalizar a compra (pagamento simulado)",
)
def criar_pedido(
    dados: PedidoEntrada,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Compra todas as peças do carrinho e entrega no endereço cadastrado.
    Não há cobrança real: o pagamento é apenas simulado.
    """
    return finalizar_compra(db, usuario, dados.total_confirmado)


@router.get("", response_model=list[PedidoPublico], summary="Listar meus pedidos")
def listar_pedidos(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    consulta = (
        select(Pedido)
        .where(Pedido.usuario_id == usuario.id)
        .order_by(Pedido.criado_em.desc(), Pedido.id.desc())
    )
    return db.scalars(consulta).all()


@router.get("/{pedido_id}", response_model=PedidoPublico, summary="Ver um pedido")
def ver_pedido(
    pedido_id: int,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    pedido = db.get(Pedido, pedido_id)
    # Pedido de outra pessoa responde 404 (e não 403) de propósito:
    # assim ninguém descobre quais números de pedido existem.
    if pedido is None or pedido.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado.")
    return pedido
