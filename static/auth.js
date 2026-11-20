'use strict';

const registrationForm = document.querySelector('#register-form');

/**
 * Compara os campos de senha durante a digitação e na submissão do formulário.
 * Os eventos input e submit atualizam a validade HTML, sem enviar ou guardar
 * credenciais em JavaScript; a rota POST /cadastro repete a mesma validação.
 */
function validatePasswordMatch() {
  const password = document.querySelector('#senha');
  const confirmation = document.querySelector('#confirmacao');
  if (!password || !confirmation) return true;
  confirmation.setCustomValidity(
    password.value === confirmation.value ? '' : 'A senha e a confirmação precisam corresponder.'
  );
  return confirmation.validity.valid;
}

if (registrationForm) {
  registrationForm.addEventListener('input', validatePasswordMatch);
  registrationForm.addEventListener('submit', event => {
    if (!validatePasswordMatch()) {
      event.preventDefault();
      registrationForm.reportValidity();
    }
  });
}
