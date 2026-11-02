/* login.js — usado em index.html */

// Quem já está logado vai direto para a tela inicial
if (estaLogado()) {
    window.location.href = "home.html";
}

const formLogin = document.querySelector(".login-form");
const caixaMensagemLogin = document.getElementById("mensagem-login");

// Aviso vindo da tela "Redefinir senha"
if (new URLSearchParams(location.search).get("aviso") === "senha-alterada") {
    mostrarMensagem(caixaMensagemLogin, "Senha alterada com sucesso! Entre com a nova senha.", "sucesso");
}

formLogin.addEventListener("submit", async (evento) => {
    // Impede o envio "tradicional" do formulário (que recarregaria a página)
    evento.preventDefault();
    esconderMensagem(caixaMensagemLogin);

    const botao = formLogin.querySelector("button[type=submit]");
    botao.disabled = true;

    // O login usa o formato de formulário do padrão OAuth2:
    // "username" é o e-mail e "password" é a senha.
    const dados = new URLSearchParams();
    dados.append("username", formLogin.email.value.trim());
    dados.append("password", formLogin.senha.value);

    try {
        const resposta = await apiFetch("/auth/login", { method: "POST", body: dados });
        salvarToken(resposta.access_token);
        window.location.href = "home.html";
    } catch (erro) {
        mostrarMensagem(caixaMensagemLogin, erro.message);
        botao.disabled = false;
    }
});
