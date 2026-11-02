/* meus_anuncios.js — usado em meus_anuncios.html */

const listaAnuncios = document.getElementById("lista-anuncios");
const semAnuncios = document.getElementById("sem-anuncios");
const caixaMensagemAnuncios = document.getElementById("mensagem-anuncios");


/* Mensagem vinda da tela Vender (meus_anuncios.html?aviso=criado) */
const avisos = {
    criado: "Anúncio publicado com sucesso!",
    editado: "Anúncio atualizado com sucesso!",
};
const aviso = new URLSearchParams(location.search).get("aviso");
if (avisos[aviso]) {
    mostrarMensagem(caixaMensagemAnuncios, avisos[aviso], "sucesso");
}


/*
 * Monta o cartão de um anúncio.
 * Usamos createElement + textContent em vez de montar HTML com o texto
 * do usuário: assim um título como "<script>..." aparece como texto
 * e nunca é executado.
 */
function criarCartao(produto) {
    const cartao = document.createElement("article");
    cartao.className = "anuncio";

    const caixaImagem = document.createElement("div");
    caixaImagem.className = "anuncio-imagem";
    const img = document.createElement("img");
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    caixaImagem.append(img);

    const info = document.createElement("div");
    info.className = "anuncio-info";
    const titulo = document.createElement("h2");
    titulo.textContent = produto.nome;
    const preco = document.createElement("p");
    preco.textContent = formatarPreco(produto.preco);
    const status = document.createElement("span");
    const vendido = produto.status === "vendido";
    status.className = "anuncio-status" + (vendido ? " vendido" : "");
    status.textContent = vendido ? "Vendido" : "Disponível";
    info.append(titulo, preco, status);

    cartao.append(caixaImagem, info);

    if (vendido) {
        // Peça vendida vira histórico: sem editar nem excluir
        const avisoVendido = document.createElement("p");
        avisoVendido.className = "anuncio-aviso";
        avisoVendido.textContent = "Peça vendida: o anúncio não pode mais ser alterado.";
        cartao.append(avisoVendido);
    } else {
        const editar = document.createElement("button");
        editar.type = "button";
        editar.className = "botao-editar";
        editar.textContent = "Editar anúncio";
        editar.addEventListener("click", () => {
            window.location.href = `vender.html?id=${produto.id}`;
        });

        const excluir = document.createElement("button");
        excluir.type = "button";
        excluir.className = "botao-remover";
        excluir.textContent = "Excluir anúncio";
        excluir.addEventListener("click", () => excluirAnuncio(produto));

        cartao.append(editar, excluir);
    }

    return cartao;
}


async function carregarAnuncios() {
    try {
        const produtos = await apiFetch("/produtos/meus");
        listaAnuncios.replaceChildren(...produtos.map(criarCartao));
        semAnuncios.classList.toggle("escondido", produtos.length > 0);
    } catch (erro) {
        mostrarMensagem(caixaMensagemAnuncios, erro.message);
    }
}


async function excluirAnuncio(produto) {
    if (!confirm(`Excluir o anúncio "${produto.nome}"? Esta ação não pode ser desfeita.`)) {
        return;
    }
    try {
        await apiFetch(`/produtos/${produto.id}`, { method: "DELETE" });
        mostrarMensagem(caixaMensagemAnuncios, "Anúncio excluído.", "sucesso");
        carregarAnuncios();
    } catch (erro) {
        mostrarMensagem(caixaMensagemAnuncios, erro.message);
    }
}


carregarAnuncios();
