// Validación del formulario de contacto
document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    form.addEventListener('submit', function (event) {
        event.preventDefault();

        const nombre = document.getElementById('nombre').value.trim();
        const email = document.getElementById('email').value.trim();
        const mensaje = document.getElementById('mensaje').value.trim();

        if (nombre === '' || email === '' || mensaje === '') {
            alert('Por favor, completa todos los campos.');
            return;
        }

        if (!validateEmail(email)) {
            alert('Por favor, introduce un correo electrónico válido.');
            return;
        }

        alert('Mensaje enviado con éxito. ¡Gracias por contactarnos!');
        form.reset();
    });
});

// Función para validar el formato del correo electrónico
function validateEmail(email) {
    const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return regex.test(email);
}

// Agregar efecto de zoom a las imágenes de la galería
document.addEventListener('DOMContentLoaded', function () {
    const images = document.querySelectorAll('.galeria img');
    images.forEach(image => {
        image.addEventListener('click', function () {
            image.classList.toggle('zoomed');
        });
    });
});

// Filtrar obras por título o precio
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('busqueda');
    const figures = document.querySelectorAll('.galeria figure');

    searchInput.addEventListener('input', function (event) {
        const query = event.target.value.toLowerCase();

        figures.forEach(figure => {
            const caption = figure.querySelector('figcaption').innerText.toLowerCase();
            if (caption.includes(query)) {
                figure.style.display = 'block';
            } else {
                figure.style.display = 'none';
            }
        });
    });
});

// Animar secciones al desplazarse
document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    });

    sections.forEach(section => {
        observer.observe(section);
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const comentarioLista = document.getElementById('comentarios-lista');
    const comentarioTexto = document.getElementById('comentario-texto');
    const comentarioEnviar = document.getElementById('comentario-enviar');

    comentarioEnviar.addEventListener('click', function () {
        const texto = comentarioTexto.value.trim();
        if (texto === '') {
            alert('Por favor, escribe un comentario.');
            return;
        }

        const nuevoComentario = document.createElement('li');
        nuevoComentario.textContent = texto;
        comentarioLista.appendChild(nuevoComentario);
        comentarioTexto.value = '';
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.createElement('button');
    toggle.textContent = 'Modo Oscuro';
    toggle.style.position = 'fixed';
    toggle.style.top = '10px';
    toggle.style.right = '10px';
    document.body.appendChild(toggle);

    toggle.addEventListener('click', function () {
        document.body.classList.toggle('dark-mode');
        toggle.textContent = document.body.classList.contains('dark-mode') ? 'Modo Claro' : 'Modo Oscuro';
    });
});
function compartir(titulo) {
    const url = encodeURIComponent(window.location.href);
    const texto = encodeURIComponent(`Mira esta obra: ${titulo}`);
    window.open(`https://twitter.com/intent/tweet?text=${texto}&url=${url}`, '_blank');
}

