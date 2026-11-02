/* redefinir_senha.js — usado em redefinir_senha.html?token=...
 * (o link chega "por e-mail"; neste projeto ele aparece no terminal do servidor)
 */

const formRedefinir = document.querySelector(".redefinir-form");
const caixaMensagemRedefinir = document.getElementById("mensagem-redefinir");
const tokenRedefinicao = new URLSearchParams(location.search).get("token");
const botaoConfirmar = formRedefinir.querySelector("button[type=submit]");

if (!tokenRedefinicao) {
    mostrarMensagem(caixaMensagemRedefinir,
        "Link incompleto. Abra o link recebido ou peça um novo em \"Esqueci minha senha\".");
    botaoConfirmar.disabled = true;
}

formRedefinir.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    esconderMensagem(caixaMensagemRedefinir);

    const novaSenha = formRedefinir["nova-senha"].value;
    if (novaSenha.length < 8) {
        mostrarMensagem(caixaMensagemRedefinir, "A nova senha deve ter pelo menos 8 caracteres.");
        return;
    }
    if (novaSenha !== formRedefinir["confirmar-senha"].value) {
        mostrarMensagem(caixaMensagemRedefinir, "As senhas não são iguais.");
        return;
    }

    botaoConfirmar.disabled = true;
    try {
        await apiFetch("/auth/redefinir-senha", {
            method: "POST",
            body: { token: tokenRedefinicao, nova_senha: novaSenha },
        });
        // Volta para o login com um aviso de sucesso
        window.location.href = "index.html?aviso=senha-alterada";
    } catch (erro) {
        mostrarMensagem(caixaMensagemRedefinir, erro.message);
        botaoConfirmar.disabled = false;
    }
});
