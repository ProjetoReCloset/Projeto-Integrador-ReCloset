/* esqueci_senha.js — usado em esqueci_senha.html */

const formSenha = document.querySelector(".senha-form");
const caixaMensagemSenha = document.getElementById("mensagem-senha");

formSenha.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemSenha);

    if (!formSenha.email.checkValidity() || !formSenha.email.value.trim()) {
        mostrarMensagem(caixaMensagemSenha, "Informe um e-mail válido.");
        return;
    }

    const botao = formSenha.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
        const resposta = await apiFetch("/auth/esqueci-senha", {
            method: "POST",
            body: { email: formSenha.email.value.trim() },
        });
        // A mensagem é a mesma exista ou não a conta (ninguém descobre quem é cliente)
        mostrarMensagem(caixaMensagemSenha, resposta.mensagem, "sucesso");
    } catch (erro) {
        mostrarMensagem(caixaMensagemSenha, erro.message);
    } finally {
        botao.disabled = false;
    }
});
