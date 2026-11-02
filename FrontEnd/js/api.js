/*
 * api.js — funções compartilhadas por todas as páginas.
 *
 * - apiFetch(): chama a API e já envia o token de login.
 * - salvarToken() / sair(): guardam e apagam o login do navegador.
 * - exigirLogin(): usado nas páginas privadas.
 */

// Se o site foi aberto pelo próprio FastAPI (porta 8000), a API está no
// mesmo endereço. Caso contrário (ex.: Live Server), apontamos para ela.
const API_URL = location.port === "8000" ? "/api" : "http://localhost:8000/api";

const CHAVE_TOKEN = "recloset_token";


function obterToken() {
    return localStorage.getItem(CHAVE_TOKEN);
}

function salvarToken(token) {
    localStorage.setItem(CHAVE_TOKEN, token);
}

function estaLogado() {
    return obterToken() !== null;
}

function sair() {
    localStorage.removeItem(CHAVE_TOKEN);
    window.location.href = "index.html";
}


/*
 * Redireciona para o login se não houver token.
 * ATENÇÃO: isto é só para a experiência do usuário. A proteção de
 * verdade está no backend, que recusa (401) qualquer requisição sem
 * token válido — não dá para "burlar" apagando este código.
 */
function exigirLogin() {
    if (!estaLogado()) {
        window.location.href = "index.html";
    }
}


/*
 * Faz uma requisição para a API.
 *   caminho: ex. "/usuarios/me"
 *   opcoes:  as mesmas do fetch() (method, body, headers...)
 * Devolve os dados em JSON ou lança um Error com a mensagem do servidor.
 */
async function apiFetch(caminho, opcoes = {}) {
    const headers = { ...(opcoes.headers || {}) };

    const token = obterToken();
    if (token) {
        headers["Authorization"] = "Bearer " + token;
    }

    // Objetos comuns viram JSON. (FormData e URLSearchParams vão como estão.)
    let body = opcoes.body;
    if (body && !(body instanceof FormData) && !(body instanceof URLSearchParams)) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(body);
    }

    let resposta;
    try {
        resposta = await fetch(API_URL + caminho, { ...opcoes, headers, body });
    } catch (erro) {
        throw new Error("Não foi possível conectar ao servidor. Ele está ligado?");
    }

    // 204 = sucesso sem conteúdo (ex.: exclusão)
    const dados = resposta.status === 204 ? null : await resposta.json().catch(() => null);

    if (!resposta.ok) {
        // Token vencido: apaga e, numa página privada, volta para o login.
        // Em páginas públicas (opcoes.publica = true) a pessoa continua onde está.
        if (resposta.status === 401 && token) {
            localStorage.removeItem(CHAVE_TOKEN);
            if (!opcoes.publica) {
                window.location.href = "index.html";
            }
        }
        const mensagem = dados && typeof dados.detail === "string"
            ? dados.detail
            : "Ocorreu um erro. Tente novamente.";
        const erro = new Error(mensagem);
        erro.status = resposta.status; // ex.: 404, para a página decidir o que fazer
        throw erro;
    }

    return dados;
}


/* Mostra uma mensagem dentro de um elemento <div class="mensagem"> */
function mostrarMensagem(elemento, texto, tipo = "erro") {
    elemento.textContent = texto;
    elemento.className = "mensagem visivel " + tipo;
}

function esconderMensagem(elemento) {
    elemento.className = "mensagem";
    elemento.textContent = "";
}


/*
 * Endereço completo de um arquivo enviado (foto).
 * O banco guarda só "perfis/abc.jpg"; o arquivo fica em /uploads/perfis/abc.jpg
 * Sem foto, devolve a imagem padrão informada.
 */
function urlArquivo(caminho, padrao = "img/sem_foto.svg") {
    if (!caminho) {
        return padrao;
    }
    return API_URL.replace(/\/api$/, "") + "/uploads/" + caminho;
}


/* Pedidos: 7 -> "#0007" e o texto/estilo de cada status */
function numeroPedido(id) {
    return "#" + String(id).padStart(4, "0");
}

const STATUS_PEDIDO = {
    confirmado: { texto: "Confirmado", classe: "confirmado" },
    enviado: { texto: "A caminho", classe: "andamento" },
    entregue: { texto: "Entregue", classe: "entregue" },
};


/* Formata 45.5 -> "R$ 45,50" */
function formatarPreco(valor) {
    return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
