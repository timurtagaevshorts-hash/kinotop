// Kino kodini tekshirish
function getFilm() {
    const kod = document.getElementById('filmKod').value;
    if (!kod) {
        alert('Iltimos, film kodini kiriting!');
        return;
    }
    window.location.href = `/film/${kod}`;
}

// Enter tugmasi
document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('filmKod');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') getFilm();
        });
    }
});

// Film kartasiga bosganda
function filmgaOgit(kod) {
    window.location.href = `/film/${kod}`;
}

// Shorts ochish
function shortOchish(id) {
    window.location.href = `/shorts/${id}`;
}