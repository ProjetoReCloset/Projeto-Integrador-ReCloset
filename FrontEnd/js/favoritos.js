/* favoritos.js — usado em favoritos.html (página privada) */

const listaFavoritos = document.getElementById("lista-favoritos");
const estadoFavoritos = document.getElementById("estado-favoritos");
const botaoLimpar = document.getElementById("botao-limpar");

// Mesmo coração cheio que já existia no HTML desta página
const CAMINHO_CORACAO = "m480-120-58-52q-101-91-167-157T149-449q-40-54-56-98t-16-92q0-89 60.5-149.5T287-849q52 0 98 24.5t75 69.5q29-45 75-69.5t98-24.5q89 0 149.5 60.5T843-639q0 48-16 92t-56 98q-40 54-106 120T538-172l-58 52Z";


function criarIconeCoracao() {
    // SVG precisa de createElementNS (o "namespace" do SVG), não de createElement
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 -960 960 960");
    const caminho = document.createElementNS("http://www.w3.org/2000/svg", "path");
    caminho.setAttribute("d", CAMINHO_CORACAO);
    svg.append(caminho);
    return svg;
}


/* Cartão no mesmo formato do HTML original da página */
function criarCartaoFavorito(produto) {
    const link = `produto.html?id=${produto.id}`;
    const vendido = produto.status === "vendido";

    const cartao = document.createElement("article");
    cartao.className = "produto" + (vendido ? " vendido" : "");

    const linkImagem = document.createElement("a");
    linkImagem.href = link;
    const img = document.createElement("img");
    img.className = "produto-imagem";
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    linkImagem.append(img);

    const info = document.createElement("div");
    info.className = "produto-info";
    const titulo = document.createElement("h2");
    const linkTitulo = document.createElement("a");
    linkTitulo.href = link;
    linkTitulo.textContent = produto.nome;
    titulo.append(linkTitulo);
    const tamanho = document.createElement("p");
    tamanho.textContent = `Tamanho: ${produto.tamanho || "único"}`;
    const preco = document.createElement("strong");
    preco.textContent = formatarPreco(produto.preco);
    info.append(titulo, tamanho, preco);

    if (vendido) {
        const etiqueta = document.createElement("p");
        const span = document.createElement("span");
        span.className = "etiqueta-vendido";
        span.textContent = "Vendido";
        etiqueta.append(span);
        info.append(etiqueta);
    }

    const remover = document.createElement("button");
    remover.type = "button";
    remover.className = "botao-favorito";
    remover.setAttribute("aria-label", `Remover ${produto.nome} dos favoritos`);
    remover.append(criarIconeCoracao());
    remover.addEventListener("click", () => removerFavorito(produto, cartao, remover));

    cartao.append(linkImagem, info, remover);
    return cartao;
}


function atualizarEstado() {
    const vazio = listaFavoritos.children.length === 0;
    botaoLimpar.hidden = vazio;
    if (vazio) {
        estadoFavoritos.innerHTML =
            'Você ainda não tem favoritos. Toque no ♡ das peças que gostar. <a href="ver_mais.html">Ver peças</a>';
    } else {
        estadoFavoritos.textContent = "";
    }
}


async function carregarListaFavoritos() {
    try {
        const produtos = await apiFetch("/favoritos");
        listaFavoritos.replaceChildren(...produtos.map(criarCartaoFavorito));
        atualizarEstado();
    } catch (erro) {
        estadoFavoritos.textContent = "Não foi possível carregar seus favoritos. " + erro.message;
    }
}


async function removerFavorito(produto, cartao, botao) {
    botao.disabled = true;
    try {
        await apiFetch(`/favoritos/${produto.id}`, { method: "DELETE" });
        cartao.remove(); // tira da tela sem recarregar a lista inteira
        atualizarEstado();
    } catch (erro) {
        alert(erro.message);
        botao.disabled = false;
    }
}


botaoLimpar.addEventListener("click", async () => {
    if (!confirm("Remover todas as peças dos seus favoritos?")) {
        return;
    }
    try {
        await apiFetch("/favoritos", { method: "DELETE" });
        listaFavoritos.replaceChildren();
        atualizarEstado();
    } catch (erro) {
        alert(erro.message);
    }
});


carregarListaFavoritos();
