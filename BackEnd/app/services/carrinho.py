"""
Regras do carrinho e cálculo dos valores.

IMPORTANTE: os valores são SEMPRE calculados aqui, no servidor, a partir
dos preços que estão no banco. O navegador nunca envia preço nem total:
assim ninguém consegue "editar o HTML" e pagar R$ 1,00 numa peça.

Esta função também será usada na finalização da compra.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import VALOR_ENTREGA
from app.models import ItemCarrinho, Usuario


def itens_do_carrinho(db: Session, usuario: Usuario) -> list[ItemCarrinho]:
    consulta = (
        select(ItemCarrinho)
        .where(ItemCarrinho.usuario_id == usuario.id)
        .order_by(ItemCarrinho.adicionado_em.desc(), ItemCarrinho.id.desc())
    )
    return list(db.scalars(consulta).all())


def calcular_resumo(db: Session, usuario: Usuario) -> dict:
    """
    Monta o carrinho com os valores:
      subtotal      = soma dos preços das peças AINDA disponíveis
      valor_entrega = valor fixo por pedido (só se houver peça para entregar)
      total         = subtotal + valor_entrega

    Peças que foram vendidas para outra pessoa depois de entrarem no
    carrinho aparecem marcadas como indisponíveis e não entram na conta.
    """
    itens = itens_do_carrinho(db, usuario)

    disponiveis = [item for item in itens if item.produto.status == "disponivel"]
    indisponiveis = [item for item in itens if item.produto.status != "disponivel"]

    subtotal = sum((item.produto.preco for item in disponiveis), Decimal("0.00"))
    valor_entrega = VALOR_ENTREGA if disponiveis else Decimal("0.00")

    return {
        "itens": [
            {"produto": item.produto, "disponivel": item.produto.status == "disponivel"}
            for item in itens
        ],
        "quantidade": len(disponiveis),
        "subtotal": subtotal,
        "valor_entrega": valor_entrega,
        "total": subtotal + valor_entrega,
        # Só dá para finalizar se houver algo para comprar e nenhuma peça vendida no meio
        "pode_finalizar": bool(disponiveis) and not indisponiveis,
    }
