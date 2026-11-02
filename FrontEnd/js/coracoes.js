/* coracoes.js — botões de favoritar (♡ / ♥) nas páginas do catálogo
 *
 * Qualquer botão com o atributo data-produto-id vira um coração:
 *   <button class="favoritar" data-produto-id="7" data-vendedor-id="3">♡</button>
 *
 * Uso na página:
 *   await carregarFavoritos();      // descobre quais já são favoritos
 *   pintarCoracoes();               // depois de criar os cartões
 *   ativarCoracoes(elementoLista);  // uma vez, para tratar os cliques
 */

let idsFavoritos = new Set(); // ids dos produtos favoritados pela pessoa logada
let meuId = null;             // id da pessoa logada (para esconder o coração nos anúncios dela)


async function carregarFavoritos() {
    idsFavoritos = new Set();
    meuId = null;
    if (!estaLogado()) {
        return;
    }
    try {
        // publica: true -> se o login venceu, a página pública continua funcionando
        const [ids, eu] = await Promise.all([
            apiFetch("/favoritos/ids", { publica: true }),
            apiFetch("/usuarios/me", { publica: true }),
        ]);
        idsFavoritos = new Set(ids);
        meuId = eu.id;
    } catch {
        // sem login válido: todos os corações ficam vazios
    }
}


/* Deixa cada coração cheio (♥) ou vazio (♡) conforme a lista */
function pintarCoracoes(raiz = document) {
    raiz.querySelectorAll("[data-produto-id]").forEach((botao) => {
        const favoritado = idsFavoritos.has(Number(botao.dataset.produtoId));
        botao.textContent = favoritado ? "♥" : "♡";
        botao.classList.toggle("favoritado", favoritado);
        botao.setAttribute("aria-pressed", favoritado); // leitores de tela anunciam o estado
        // Ninguém favorita o próprio anúncio: o coração some
        botao.hidden = meuId !== null && Number(botao.dataset.vendedorId) === meuId;
    });
}


/* Liga ou desliga o favorito de um produto. Devolve o novo estado (true/false). */
async function alternarFavorito(produtoId) {
    if (!estaLogado()) {
        window.location.href = "index.html"; // precisa entrar para favoritar
        return false;
    }
    if (idsFavoritos.has(produtoId)) {
        await apiFetch(`/favoritos/${produtoId}`, { method: "DELETE" });
        idsFavoritos.delete(produtoId);
    } else {
        await apiFetch(`/favoritos/${produtoId}`, { method: "POST" });
        idsFavoritos.add(produtoId);
    }
    return idsFavoritos.has(produtoId);
}


/*
 * "Delegação de eventos": em vez de colocar um ouvinte em cada coração,
 * colocamos UM no elemento que contém a lista. Assim funciona também
 * para cartões criados depois (ao trocar o filtro, por exemplo).
 */
function ativarCoracoes(container) {
    container.addEventListener("click", async (evento) => {
        const botao = evento.target.closest("[data-produto-id]");
        if (!botao) return;
        evento.preventDefault();

        botao.disabled = true; // evita dois cliques seguidos
        try {
            await alternarFavorito(Number(botao.dataset.produtoId));
            pintarCoracoes(container);
        } catch (erro) {
            alert(erro.message); // ex.: "Você não pode favoritar o seu próprio anúncio."
        } finally {
            botao.disabled = false;
        }
    });
}
