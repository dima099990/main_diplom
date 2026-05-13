// Burger menu
const burger = document.getElementById('burger');
const navLinks = document.getElementById('navLinks');
if (burger) {
  burger.addEventListener('click', () => navLinks.classList.toggle('open'));
}

// Scroll animations
const animEls = document.querySelectorAll('[data-animate]');
if (animEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.1 });
  animEls.forEach(el => obs.observe(el));
}

// Auto-dismiss alerts
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => el.style.opacity = '0', 4000);
  setTimeout(() => el.remove(), 4500);
});

// Ajax form submission for hero form
const heroForm = document.getElementById('heroForm');
if (heroForm) {
  heroForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = heroForm.querySelector('button[type=submit]');
    btn.disabled = true; btn.textContent = 'Отправляем...';
    const res = await fetch(heroForm.action, {
      method: 'POST',
      body: new FormData(heroForm),
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const data = await res.json();
    if (data.ok) {
      heroForm.style.display = 'none';
      document.getElementById('formSuccess').style.display = 'block';
    } else {
      btn.disabled = false; btn.textContent = 'Отправить заявку';
      alert(data.error || 'Ошибка, попробуйте снова');
    }
  });
}
