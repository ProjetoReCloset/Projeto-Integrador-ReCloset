"""
Finalização da compra — a parte mais delicada do sistema.

O PROBLEMA: cada peça é única. Imagine a Ana e o Bruno clicando em
"Confirmar pedido" no mesmo segundo, com a mesma blusa no carrinho.
Se o código fizesse:

    1. SELECT status FROM produto WHERE id = 7     -> "disponivel"  (Ana)
    2. SELECT status FROM produto WHERE id = 7     -> "disponivel"  (Bruno)
    3. UPDATE produto SET status = 'vendido' ...                    (Ana)
    4. UPDATE produto SET status = 'vendido' ...                    (Bruno)

os dois "comprariam" a mesma peça, porque os dois leram "disponível"
antes de qualquer um gravar.

A SOLUÇÃO (atualização condicional): verificar e marcar num único comando.

    UPDATE produto SET status = 'vendido'
    WHERE id = 7 AND status = 'disponivel'

O banco executa esse comando de forma atômica: só UMA das duas compras
consegue mudar a linha. Para a outra, o comando afeta 0 linhas
(rowcount == 0), e então desfazemos tudo (rollback) e avisamos que a peça
acabou de ser vendida.

Tudo acontece dentro de UMA transação: ou o pedido inteiro é gravado
(pedido + itens + peças vendidas + carrinho limpo), ou nada é gravado.

Segunda proteção: a coluna item_pedido.produto_id é UNIQUE. Mesmo que
houvesse um erro no código, o banco recusaria a mesma peça em dois pedidos.
"""
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import VALOR_ENTREGA
from app.models import Endereco, ItemCarrinho, ItemPedido, Pedido, Produto, Usuario


def formatar_endereco(endereco: Endereco) -> str:
    complemento = f" - {endereco.complemento}" if endereco.complemento else ""
    return (f"{endereco.rua}, {endereco.numero}{complemento}\n"
            f"{endereco.bairro} - {endereco.cidade}/{endereco.estado}\n"
            f"CEP: {endereco.cep}")


def finalizar_compra(db: Session, usuario: Usuario, total_confirmado: Decimal | None) -> Pedido:
    # ---------- 1. Verificações antes de começar ----------
    if usuario.endereco is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cadastre um endereço de entrega antes de finalizar.")

    itens = db.scalars(select(ItemCarrinho).where(ItemCarrinho.usuario_id == usuario.id)).all()
    if not itens:
        raise HTTPException(status.HTTP_409_CONFLICT, "Seu carrinho está vazio.")

    vendidas = [item.produto.nome for item in itens if item.produto.status != "disponivel"]
    if vendidas:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Estas peças já foram vendidas: " + ", ".join(vendidas) + ". Remova-as do carrinho.",
        )

    ids = [item.produto_id for item in itens]

    try:
        # ---------- 2. Reservar as peças (atualização condicional) ----------
        for produto_id in ids:
            resultado = db.execute(
                update(Produto)
                .where(
                    Produto.id == produto_id,
                    Produto.status == "disponivel",       # só se ainda estiver disponível
                    Produto.vendedor_id != usuario.id,    # ninguém compra de si mesmo
                )
                .values(status="vendido")
            )
            if resultado.rowcount != 1:
                # Outra pessoa comprou esta peça entre a nossa verificação e agora
                db.rollback()  # desfaz as peças que já tínhamos marcado
                nome = db.get(Produto, produto_id).nome
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f'A peça "{nome}" acabou de ser vendida para outra pessoa. Seu pedido não foi feito.',
                )

        # ---------- 3. Calcular os valores com os preços do banco ----------
        produtos = db.scalars(select(Produto).where(Produto.id.in_(ids))).all()
        subtotal = sum((p.preco for p in produtos), Decimal("0.00"))
        total = subtotal + VALOR_ENTREGA

        # O navegador pode informar o total que a pessoa VIU na tela.
        # Não usamos esse valor para nada além de conferir: se o preço mudou
        # enquanto ela revisava, paramos e pedimos para revisar de novo.
        if total_confirmado is not None and total_confirmado != total:
            db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Os valores do seu pedido mudaram. Revise o carrinho antes de confirmar.",
            )

        # ---------- 4. Registrar o pedido ----------
        pedido = Pedido(
            usuario_id=usuario.id,
            subtotal=subtotal,
            valor_entrega=VALOR_ENTREGA,
            total=total,
            status="confirmado",
            endereco_entrega=formatar_endereco(usuario.endereco),  # cópia do endereço
            itens=[ItemPedido(produto_id=p.id, preco=p.preco) for p in produtos],  # preço da hora
        )
        db.add(pedido)

        # ---------- 5. Esvaziar o carrinho ----------
        # (o carrinho de OUTRAS pessoas com estas peças continua, e lá elas
        # aparecem como "vendida para outra pessoa")
        db.execute(delete(ItemCarrinho).where(ItemCarrinho.usuario_id == usuario.id))

        db.commit()  # só agora tudo é gravado de uma vez
    except IntegrityError:
        # Última barreira: o UNIQUE de item_pedido.produto_id recusou uma venda duplicada
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Uma das peças já foi vendida. Seu pedido não foi feito.")

    db.refresh(pedido)
    return pedido
