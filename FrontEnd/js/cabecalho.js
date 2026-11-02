/* cabecalho.js — barra de pesquisa do cabeçalho (usado em todas as páginas com o menu)
 *
 * Ao apertar Enter, abre "Ver todos" com o termo pesquisado:
 *   ver_mais.html?busca=blusa
 */

const campoPesquisa = document.querySelector(".pesquisa input");

if (campoPesquisa) {
    // Se já estamos vendo uma busca, deixa o termo escrito na barra
    const buscaAtual = new URLSearchParams(location.search).get("busca");
    if (buscaAtual) {
        campoPesquisa.value = buscaAtual;
    }

    campoPesquisa.addEventListener("keydown", (evento) => {
        if (evento.key !== "Enter") {
            return;
        }
        const termo = campoPesquisa.value.trim();
        // encodeURIComponent: espaços e acentos viram um texto seguro para a URL
        window.location.href = termo
            ? "ver_mais.html?busca=" + encodeURIComponent(termo)
            : "ver_mais.html";
    });
}
