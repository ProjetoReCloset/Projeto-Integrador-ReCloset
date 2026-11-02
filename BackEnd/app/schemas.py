"""
Schemas (Pydantic): definem o formato dos dados que ENTRAM e SAEM da API.

- Schemas de entrada validam o que o navegador enviou.
- Schemas de saída escolhem o que é devolvido. Repare que nenhum
  schema de saída tem o campo senha_hash: ele nunca sai do servidor.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

Sexo = Literal["feminino", "masculino", "outros"]


def _marcar_como_utc(data: datetime) -> datetime:
    """
    Gravamos as datas em UTC, mas o SQLite não guarda o fuso horário.
    Sem o fuso, o navegador acharia que "00:45" é horário de Brasília
    e mostraria o dia errado. Aqui recolocamos a informação "isto é UTC".
    """
    return data if data.tzinfo else data.replace(tzinfo=timezone.utc)


# Use este tipo em toda data que SAI da API
DataUTC = Annotated[datetime, AfterValidator(_marcar_como_utc)]


class EntradaBase(BaseModel):
    # Remove espaços no começo e no fim de todos os textos recebidos
    model_config = ConfigDict(str_strip_whitespace=True)


# ---------- Usuário ----------

def _validar_senha(senha: str) -> str:
    # O bcrypt só considera os primeiros 72 bytes da senha.
    # Letras com acento ocupam 2 bytes, por isso contamos bytes, não letras.
    if len(senha.encode("utf-8")) > 72:
        raise ValueError("A senha é longa demais")
    return senha


def _validar_telefone(telefone: str | None) -> str | None:
    if not telefone:
        return None
    numeros = "".join(c for c in telefone if c.isdigit())
    if len(numeros) not in (10, 11):
        raise ValueError("Informe DDD + número (10 ou 11 dígitos)")
    return numeros


class UsuarioCadastro(EntradaBase):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    sexo: Sexo

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, valor: str) -> str:
        # "Maria@Email.com" e "maria@email.com" são o mesmo e-mail
        return valor.lower()

    @field_validator("senha")
    @classmethod
    def senha_valida(cls, valor: str) -> str:
        return _validar_senha(valor)


class UsuarioAtualizacao(EntradaBase):
    """Todos os campos são opcionais: só muda o que foi enviado."""
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    sexo: Sexo | None = None
    telefone: str | None = Field(default=None, max_length=20)
    descricao: str | None = Field(default=None, max_length=300)

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, valor: str | None) -> str | None:
        return valor.lower() if valor else valor

    @field_validator("telefone")
    @classmethod
    def telefone_valido(cls, valor: str | None) -> str | None:
        return _validar_telefone(valor)


class UsuarioPublico(BaseModel):
    """O que a API devolve sobre um usuário (sem senha!)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    sexo: str
    telefone: str | None
    descricao: str | None
    foto: str | None
    criado_em: DataUTC


class EsqueciSenhaEntrada(EntradaBase):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_minusculo(cls, valor: str) -> str:
        return valor.lower()


class RedefinirSenhaEntrada(EntradaBase):
    token: str = Field(min_length=20, max_length=200)
    nova_senha: str = Field(min_length=8, max_length=72)

    @field_validator("nova_senha")
    @classmethod
    def senha_valida(cls, valor: str) -> str:
        return _validar_senha(valor)


class Mensagem(BaseModel):
    mensagem: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResumoPerfil(BaseModel):
    """Números mostrados no topo da página de perfil."""
    produtos: int   # anúncios cadastrados (disponíveis + vendidos)
    vendas: int     # anúncios já vendidos
    favoritos: int  # produtos que o usuário favoritou


# ---------- Endereço ----------

ESTADOS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


class EnderecoEntrada(EntradaBase):
    cep: str = Field(max_length=9)
    rua: str = Field(min_length=2, max_length=150)
    numero: str = Field(min_length=1, max_length=10)
    complemento: str | None = Field(default=None, max_length=100)
    bairro: str = Field(min_length=2, max_length=100)
    cidade: str = Field(min_length=2, max_length=100)
    estado: str = Field(min_length=2, max_length=2)

    @field_validator("cep")
    @classmethod
    def cep_valido(cls, valor: str) -> str:
        numeros = "".join(c for c in valor if c.isdigit())
        if len(numeros) != 8:
            raise ValueError("deve ter 8 dígitos")
        return f"{numeros[:5]}-{numeros[5:]}"  # guarda sempre no formato 00000-000

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, valor: str) -> str:
        valor = valor.upper()
        if valor not in ESTADOS:
            raise ValueError("não é uma sigla de estado válida")
        return valor

    @field_validator("complemento")
    @classmethod
    def complemento_vazio_vira_nulo(cls, valor: str | None) -> str | None:
        return valor or None


class EnderecoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cep: str
    rua: str
    numero: str
    complemento: str | None
    bairro: str
    cidade: str
    estado: str


# ---------- Categoria ----------

class CategoriaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    slug: str


# ---------- Produto (anúncio) ----------

CategoriaSlug = Literal["feminino", "masculino", "acessorios", "calcados"]


class ProdutoEntrada(EntradaBase):
    """
    Dados de texto de um anúncio. Usado tanto no cadastro (junto com as
    fotos, como formulário) quanto na edição (como JSON).
    """
    nome: str = Field(min_length=3, max_length=120)
    # O vendedor descreve aqui também o estado de conservação da peça
    descricao: str = Field(min_length=10, max_length=2000)
    tamanho: str | None = Field(default=None, max_length=30)
    # Decimal (e não float) para não ter erro de arredondamento em dinheiro
    preco: Decimal = Field(gt=0, le=Decimal("99999.99"), decimal_places=2)
    categoria: CategoriaSlug

    @field_validator("tamanho")
    @classmethod
    def tamanho_vazio_vira_nulo(cls, valor: str | None) -> str | None:
        return valor or None


class ImagemPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    caminho: str  # o navegador acessa em /uploads/<caminho>


class VendedorPublico(BaseModel):
    """Só o necessário sobre quem vende (sem e-mail, telefone etc.)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class ItemCarrinhoPublico(BaseModel):
    produto: "ProdutoPublico"
    disponivel: bool  # False se a peça foi vendida para outra pessoa


class ResumoCarrinho(BaseModel):
    itens: list[ItemCarrinhoPublico]
    quantidade: int          # peças disponíveis
    subtotal: Decimal
    valor_entrega: Decimal
    total: Decimal
    pode_finalizar: bool


class PedidoEntrada(BaseModel):
    # Opcional: o total que a pessoa viu na tela de revisão. NÃO é usado
    # para cobrar; serve só para o servidor conferir se nada mudou.
    total_confirmado: Decimal | None = None


class ItemPedidoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    preco: Decimal                 # preço no momento da compra
    produto: "ProdutoPublico"      # nome, fotos etc.


class PedidoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    subtotal: Decimal
    valor_entrega: Decimal
    total: Decimal
    endereco_entrega: str
    criado_em: DataUTC
    itens: list[ItemPedidoPublico]


class FavoritoResposta(BaseModel):
    produto_id: int
    favoritado: bool


class ProdutoPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    descricao: str
    tamanho: str | None
    preco: Decimal
    status: str
    categoria: CategoriaPublica
    vendedor: VendedorPublico
    imagens: list[ImagemPublica]
    criado_em: DataUTC
