"""
Testes do endereço, do resumo do perfil e do envio de foto.
"""
from tests.conftest import cadastrar_e_logar

ENDERECO = {
    "cep": "15990000", "rua": "Rua Exemplo", "numero": "123", "complemento": "",
    "bairro": "Centro", "cidade": "Matão", "estado": "sp",
}

# Menor PNG válido possível (1x1 pixel)
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)


# ---------- Endereço ----------

def test_sem_endereco_devolve_404(cliente):
    auth = cadastrar_e_logar(cliente)
    assert cliente.get("/api/endereco", headers=auth).status_code == 404


def test_criar_endereco_normaliza_cep_e_estado(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.put("/api/endereco", headers=auth, json=ENDERECO)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["cep"] == "15990-000"
    assert corpo["estado"] == "SP"
    assert corpo["complemento"] is None  # texto vazio vira nulo


def test_editar_endereco_nao_cria_um_segundo(cliente):
    auth = cadastrar_e_logar(cliente)
    primeiro = cliente.put("/api/endereco", headers=auth, json=ENDERECO).json()
    resposta = cliente.put("/api/endereco", headers=auth, json={**ENDERECO, "numero": "456"})

    assert resposta.status_code == 200
    assert resposta.json()["id"] == primeiro["id"]
    assert resposta.json()["numero"] == "456"


def test_endereco_invalido(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.put("/api/endereco", headers=auth, json={**ENDERECO, "cep": "123", "estado": "XX"})

    assert resposta.status_code == 422
    assert "CEP" in resposta.json()["detail"] and "Estado" in resposta.json()["detail"]


def test_um_usuario_nao_ve_nem_altera_endereco_do_outro(cliente):
    auth_maria = cadastrar_e_logar(cliente, "maria@email.com")
    auth_joao = cadastrar_e_logar(cliente, "joao@email.com")
    cliente.put("/api/endereco", headers=auth_maria, json=ENDERECO)

    # João não tem endereço: não pode receber o da Maria
    assert cliente.get("/api/endereco", headers=auth_joao).status_code == 404
    # Ao salvar, João cria o PRÓPRIO endereço, sem mexer no da Maria
    cliente.put("/api/endereco", headers=auth_joao, json={**ENDERECO, "rua": "Rua do João"})
    assert cliente.get("/api/endereco", headers=auth_maria).json()["rua"] == "Rua Exemplo"
    # Excluir também só afeta o próprio
    cliente.delete("/api/endereco", headers=auth_joao)
    assert cliente.get("/api/endereco", headers=auth_maria).status_code == 200


def test_excluir_endereco(cliente):
    auth = cadastrar_e_logar(cliente)
    cliente.put("/api/endereco", headers=auth, json=ENDERECO)

    assert cliente.delete("/api/endereco", headers=auth).status_code == 204
    assert cliente.get("/api/endereco", headers=auth).status_code == 404


def test_endereco_exige_login(cliente):
    assert cliente.get("/api/endereco").status_code == 401
    assert cliente.put("/api/endereco", json=ENDERECO).status_code == 401


# ---------- Resumo do perfil ----------

def test_resumo_de_usuario_novo_e_zero(cliente):
    auth = cadastrar_e_logar(cliente)
    assert cliente.get("/api/usuarios/me/resumo", headers=auth).json() == {
        "produtos": 0, "vendas": 0, "favoritos": 0,
    }


# ---------- Foto de perfil ----------

def test_enviar_foto_valida(cliente):
    auth = cadastrar_e_logar(cliente)
    resposta = cliente.post("/api/usuarios/me/foto", headers=auth,
                            files={"foto": ("eu.png", PNG_1PX, "image/png")})

    assert resposta.status_code == 200
    caminho = resposta.json()["foto"]
    assert caminho.startswith("perfis/") and caminho.endswith(".png")
    # A foto fica acessível pelo navegador
    assert cliente.get(f"/uploads/{caminho}").content == PNG_1PX


def test_arquivo_disfarcado_de_imagem_e_recusado(cliente):
    auth = cadastrar_e_logar(cliente)
    # Nome e tipo dizem "jpg", mas o conteúdo é texto
    resposta = cliente.post("/api/usuarios/me/foto", headers=auth,
                            files={"foto": ("foto.jpg", b"<script>alert(1)</script>", "image/jpeg")})
    assert resposta.status_code == 415


def test_imagem_grande_demais_e_recusada(cliente):
    auth = cadastrar_e_logar(cliente)
    grande = PNG_1PX + b"0" * (1024 * 1024)  # limite nos testes é 1 MB
    resposta = cliente.post("/api/usuarios/me/foto", headers=auth,
                            files={"foto": ("grande.png", grande, "image/png")})
    assert resposta.status_code == 413


def test_trocar_foto_apaga_a_antiga(cliente):
    auth = cadastrar_e_logar(cliente)
    envio = {"foto": ("eu.png", PNG_1PX, "image/png")}
    antiga = cliente.post("/api/usuarios/me/foto", headers=auth, files=envio).json()["foto"]
    nova = cliente.post("/api/usuarios/me/foto", headers=auth, files=envio).json()["foto"]

    assert antiga != nova
    assert cliente.get(f"/uploads/{antiga}").status_code == 404
    assert cliente.get(f"/uploads/{nova}").status_code == 200
