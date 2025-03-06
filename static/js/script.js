document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    const eyes = document.querySelectorAll('.eye');

    passwordInput.addEventListener('input', () => {
        if (passwordInput.value.length > 0) {
            eyes.forEach(eye => eye.classList.add('closed'));
        } else {
            eyes.forEach(eye => eye.classList.remove('closed'));
        }
    });
});