/* carrinho.js — usado em carrinho.html (página privada)
 *
 * O navegador só MOSTRA os valores. Quem calcula subtotal, frete e
 * total é o servidor: toda resposta da API já vem com a conta pronta.
 */

const listaCarrinho = document.getElementById("lista-carrinho");
const estadoCarrinho = document.getElementById("estado-carrinho");
const resumoCompra = document.getElementById("resumo-compra");
const botaoFinalizar = document.getElementById("botao-finalizar");
const caixaMensagemCarrinho = document.getElementById("mensagem-carrinho");

// Mesmo ícone de lixeira que já existia no HTML desta página
const LINHAS_LIXEIRA = ["M3 6h18", "M8 6V4h8v2", "M19 6l-1 15H6L5 6", "M10 11v6", "M14 11v6"];


function criarIconeLixeira() {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    for (const d of LINHAS_LIXEIRA) {
        const linha = document.createElementNS("http://www.w3.org/2000/svg", "path");
        linha.setAttribute("d", d);
        svg.append(linha);
    }
    return svg;
}


/* Cartão no mesmo formato do HTML original (article.produto-carrinho) */
function criarItemCarrinho(item) {
    const produto = item.produto;
    const link = `produto.html?id=${produto.id}`;

    const cartao = document.createElement("article");
    cartao.className = "produto-carrinho" + (item.disponivel ? "" : " indisponivel");

    const caixaImagem = document.createElement("a");
    caixaImagem.className = "produto-imagem";
    caixaImagem.href = link;
    const img = document.createElement("img");
    img.src = urlArquivo(produto.imagens[0]?.caminho);
    img.alt = produto.nome;
    caixaImagem.append(img);

    const dados = document.createElement("div");
    dados.className = "produto-dados";
    const titulo = document.createElement("h2");
    const linkTitulo = document.createElement("a");
    linkTitulo.href = link;
    linkTitulo.textContent = produto.nome;
    titulo.append(linkTitulo);
    const tamanho = document.createElement("p");
    tamanho.textContent = `Tamanho: ${produto.tamanho || "único"}`;
    const preco = document.createElement("strong");
    preco.textContent = formatarPreco(produto.preco);
    dados.append(titulo, tamanho, preco);

    if (!item.disponivel) {
        const aviso = document.createElement("p");
        aviso.className = "aviso-indisponivel";
        aviso.textContent = "Esta peça foi vendida para outra pessoa. Remova do carrinho.";
        dados.append(aviso);
    }

    const excluir = document.createElement("button");
    excluir.className = "botao-excluir";
    excluir.type = "button";
    excluir.setAttribute("aria-label", `Excluir ${produto.nome}`);
    excluir.append(criarIconeLixeira());
    excluir.addEventListener("click", () => removerItem(produto.id, excluir));

    cartao.append(caixaImagem, dados, excluir);
    return cartao;
}


/* Desenha a tela a partir do resumo que veio do servidor */
function desenharCarrinho(resumo) {
    listaCarrinho.replaceChildren(...resumo.itens.map(criarItemCarrinho));

    const vazio = resumo.itens.length === 0;
    resumoCompra.hidden = vazio;
    if (vazio) {
        estadoCarrinho.innerHTML = 'Seu carrinho está vazio. <a href="ver_mais.html">Ver peças</a>';
        esconderMensagem(caixaMensagemCarrinho);
        return;
    }
    estadoCarrinho.textContent = "";

    const plural = resumo.quantidade === 1 ? "peça" : "peças";
    document.getElementById("rotulo-subtotal").textContent = `Subtotal (${resumo.quantidade} ${plural})`;
    document.getElementById("valor-subtotal").textContent = formatarPreco(resumo.subtotal);
    document.getElementById("valor-entrega").textContent = formatarPreco(resumo.valor_entrega);
    document.getElementById("valor-total").textContent = formatarPreco(resumo.total);

    botaoFinalizar.disabled = !resumo.pode_finalizar;

    const temVendida = resumo.itens.some((item) => !item.disponivel);
    if (temVendida) {
        mostrarMensagem(caixaMensagemCarrinho,
            "Uma ou mais peças do seu carrinho já foram vendidas. Remova-as para continuar.");
    } else {
        esconderMensagem(caixaMensagemCarrinho);
    }
}


async function carregarCarrinho() {
    try {
        desenharCarrinho(await apiFetch("/carrinho"));
    } catch (erro) {
        estadoCarrinho.textContent = "Não foi possível carregar o carrinho. " + erro.message;
    }
}


async function removerItem(produtoId, botao) {
    botao.disabled = true;
    try {
        // A resposta já traz o carrinho atualizado, com os novos totais
        desenharCarrinho(await apiFetch(`/carrinho/${produtoId}`, { method: "DELETE" }));
    } catch (erro) {
        mostrarMensagem(caixaMensagemCarrinho, erro.message);
        botao.disabled = false;
    }
}


botaoFinalizar.addEventListener("click", () => {
    window.location.href = "finalizar_compra.html"; // tela de revisão do pedido
});


carregarCarrinho();
