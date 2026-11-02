/* produto.js — página de detalhes: produto.html?id=7 (pública) */

const idProduto = new URLSearchParams(location.search).get("id");
const estadoProduto = document.getElementById("estado-produto");
const detalhe = document.getElementById("detalhe");
const fotoPrincipal = document.getElementById("foto-principal");


/* Troca a foto grande ao clicar numa miniatura */
function montarGaleria(produto) {
    const area = document.getElementById("miniaturas");
    area.replaceChildren();

    fotoPrincipal.src = urlArquivo(produto.imagens[0]?.caminho);
    fotoPrincipal.alt = produto.nome;

    if (produto.imagens.length < 2) {
        return; // com uma foto só, não precisa de miniaturas
    }

    produto.imagens.forEach((imagem, indice) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "miniatura" + (indice === 0 ? " ativa" : "");
        botao.setAttribute("aria-label", `Ver foto ${indice + 1}`);

        const img = document.createElement("img");
        img.src = urlArquivo(imagem.caminho);
        img.alt = "";
        botao.append(img);

        botao.addEventListener("click", () => {
            fotoPrincipal.src = img.src;
            area.querySelectorAll(".miniatura").forEach((b) => b.classList.remove("ativa"));
            botao.classList.add("ativa");
        });
        area.append(botao);
    });
}


/*
 * Botões da peça:
 *   - se é sua: aviso + "Editar anúncio"
 *   - se é de outra pessoa: "Adicionar ao carrinho" e "Favoritar"
 */
async function montarAcoes(produto) {
    const acoes = document.getElementById("acoes-produto");
    acoes.replaceChildren();

    await carregarFavoritos(); // também descobre quem está logado (meuId)

    if (meuId === produto.vendedor.id) {
        const aviso = document.createElement("p");
        aviso.className = "aviso-acao";
        aviso.textContent = "Este anúncio é seu.";
        acoes.append(aviso);

        if (produto.status === "disponivel") {
            const editar = document.createElement("a");
            editar.className = "botao-acao secundario";
            editar.href = `vender.html?id=${produto.id}`;
            editar.textContent = "Editar anúncio";
            acoes.append(editar);
        }
        return;
    }

    if (produto.status === "disponivel") {
        acoes.append(await criarBotaoCarrinho(produto));
    }

    // Peça vendida só mostra o botão se ela já estava nos favoritos (para poder tirar)
    if (produto.status === "vendido" && !idsFavoritos.has(produto.id)) {
        return;
    }

    const favoritar = document.createElement("button");
    favoritar.type = "button";
    favoritar.className = "botao-acao secundario";

    const atualizarTexto = () => {
        const sim = idsFavoritos.has(produto.id);
        favoritar.textContent = sim ? "♥ Nos seus favoritos" : "♡ Adicionar aos favoritos";
        favoritar.setAttribute("aria-pressed", sim);
    };
    atualizarTexto();

    favoritar.addEventListener("click", async () => {
        favoritar.disabled = true;
        try {
            await alternarFavorito(produto.id); // sem login, leva para a tela de login
            atualizarTexto();
        } catch (erro) {
            alert(erro.message);
        } finally {
            favoritar.disabled = false;
        }
    });
    acoes.append(favoritar);
}


/* Botão do carrinho: "Adicionar" ou, se já estiver lá, "Ver carrinho" */
async function criarBotaoCarrinho(produto) {
    const linkCarrinho = document.createElement("a");
    linkCarrinho.className = "botao-acao";
    linkCarrinho.href = "carrinho.html";
    linkCarrinho.textContent = "✓ No carrinho · Ver carrinho";

    // Já está no carrinho? (só dá para saber se a pessoa estiver logada)
    if (meuId !== null) {
        try {
            const carrinho = await apiFetch("/carrinho", { publica: true });
            if (carrinho.itens.some((item) => item.produto.id === produto.id)) {
                return linkCarrinho;
            }
        } catch {
            // se falhar, mostramos o botão de adicionar normalmente
        }
    }

    const adicionar = document.createElement("button");
    adicionar.type = "button";
    adicionar.className = "botao-acao";
    adicionar.textContent = "Adicionar ao carrinho";

    adicionar.addEventListener("click", async () => {
        if (!estaLogado()) {
            window.location.href = "index.html"; // precisa entrar para comprar
            return;
        }
        adicionar.disabled = true;
        try {
            // Só enviamos o ID: o preço quem define é o servidor
            await apiFetch(`/carrinho/${produto.id}`, { method: "POST" });
            adicionar.replaceWith(linkCarrinho);
        } catch (erro) {
            alert(erro.message); // ex.: "Esta peça já foi vendida."
            adicionar.disabled = false;
        }
    });
    return adicionar;
}


async function carregarProduto() {
    if (!idProduto) {
        estadoProduto.innerHTML = 'Peça não informada. <a href="ver_mais.html">Ver todas as peças</a>';
        return;
    }

    try {
        const produto = await apiFetch(`/produtos/${encodeURIComponent(idProduto)}`);

        document.title = `ReCloset - ${produto.nome}`;

        // Caminho: Todos os produtos › Feminino
        const caminho = document.getElementById("caminho");
        const linkCategoria = document.createElement("a");
        linkCategoria.href = `ver_mais.html?categoria=${produto.categoria.slug}`;
        linkCategoria.textContent = produto.categoria.nome;
        caminho.append(" › ", linkCategoria);

        document.getElementById("d-categoria").textContent = produto.categoria.nome;
        document.getElementById("d-nome").textContent = produto.nome;
        document.getElementById("d-preco").textContent = formatarPreco(produto.preco);
        document.getElementById("d-tamanho").textContent =
            produto.tamanho ? `Tamanho ${produto.tamanho}` : "Tamanho único";

        const status = document.getElementById("d-status");
        const disponivel = produto.status === "disponivel";
        status.textContent = disponivel ? "Disponível" : "Vendido";
        status.classList.add(disponivel ? "disponivel" : "vendido");

        document.getElementById("d-descricao").textContent = produto.descricao;
        document.getElementById("d-vendedor").textContent = produto.vendedor.nome;
        document.getElementById("d-data").textContent =
            new Date(produto.criado_em).toLocaleDateString("pt-BR");

        montarGaleria(produto);
        montarAcoes(produto);

        estadoProduto.textContent = "";
        detalhe.classList.remove("escondido");
    } catch (erro) {
        if (erro.status === 404 || erro.status === 422) {
            estadoProduto.innerHTML = 'Peça não encontrada. <a href="ver_mais.html">Ver todas as peças</a>';
        } else {
            estadoProduto.textContent = "Não foi possível carregar a peça. " + erro.message;
        }
    }
}


/* Voltar: se veio de outra página do site, volta para ela (mantém a busca) */
document.getElementById("botao-voltar").addEventListener("click", (evento) => {
    if (document.referrer.startsWith(location.origin)) {
        evento.preventDefault();
        history.back();
    }
});


carregarProduto();
