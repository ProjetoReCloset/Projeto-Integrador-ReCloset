"""
Rotas do endereço de entrega.

Cada usuário tem no máximo UM endereço. Repare que nenhuma rota recebe
o id do endereço ou do usuário: sempre usamos o usuário do token.
Assim é impossível ver ou alterar o endereço de outra pessoa.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Endereco, Usuario
from app.schemas import EnderecoEntrada, EnderecoPublico
from app.security import get_usuario_atual

router = APIRouter(prefix="/endereco", tags=["Endereço"])


@router.get("", response_model=EnderecoPublico, summary="Ver meu endereço")
def ver_endereco(usuario: Usuario = Depends(get_usuario_atual)):
    if usuario.endereco is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Você ainda não cadastrou um endereço.")
    return usuario.endereco


@router.put("", response_model=EnderecoPublico, summary="Cadastrar ou editar meu endereço")
def salvar_endereco(
    dados: EnderecoEntrada,
    response: Response,
    usuario: Usuario = Depends(get_usuario_atual),
    db: Session = Depends(get_db),
):
    """
    Usamos PUT para as duas situações: se ainda não existe endereço,
    ele é criado (resposta 201); se já existe, é substituído (resposta 200).
    """
    endereco = usuario.endereco
    if endereco is None:
        endereco = Endereco(usuario_id=usuario.id, **dados.model_dump())
        db.add(endereco)
        response.status_code = status.HTTP_201_CREATED
    else:
        for campo, valor in dados.model_dump().items():
            setattr(endereco, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        # Dois envios ao mesmo tempo tentando CRIAR o endereço:
        # o UNIQUE(usuario_id) do banco barra o segundo.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Endereço já foi salvo. Recarregue a página.")
    db.refresh(endereco)
    return endereco


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir meu endereço")
def excluir_endereco(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    if usuario.endereco is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Você ainda não cadastrou um endereço.")
    # Os pedidos antigos não são afetados: eles guardam uma cópia do endereço.
    db.delete(usuario.endereco)
    db.commit()
