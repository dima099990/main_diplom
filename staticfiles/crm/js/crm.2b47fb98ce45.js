// Toast auto-dismiss
document.querySelectorAll('.toast').forEach(t => {
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 300); }, 4000);
});

// Mobile sidebar toggle
const burger = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('crmSidebar');
if (burger && sidebar) {
  burger.addEventListener('click', () => sidebar.classList.toggle('open'));
}

// Brand → Model cascade in repair create form
const brandSel = document.getElementById('id_brand');
const modelSel = document.getElementById('id_phone_model');
if (brandSel && modelSel) {
  brandSel.addEventListener('change', function() {
    const brandId = this.value;
    if (!brandId) { modelSel.innerHTML = '<option value="">— выберите модель —</option>'; return; }
    fetch(`/api/models/${brandId}/`)
      .then(r => r.json())
      .then(data => {
        modelSel.innerHTML = '<option value="">— выберите модель —</option>';
        data.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.id; opt.textContent = m.name;
          modelSel.appendChild(opt);
        });
      });
  });
}

// Part brand→model cascade in warehouse form
const partBrandSel = document.getElementById('id_part_brand');
const partModelSel = document.getElementById('id_part_model');
if (partBrandSel && partModelSel) {
  partBrandSel.addEventListener('change', function() {
    const brandId = this.value;
    partModelSel.innerHTML = '<option value="">— все модели —</option>';
    if (!brandId) return;
    fetch(`/api/models/${brandId}/`)
      .then(r => r.json())
      .then(data => {
        data.models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.id; opt.textContent = m.name;
          partModelSel.appendChild(opt);
        });
      });
  });
}

// Confirm dangerous actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', function(e) {
    if (!confirm(this.dataset.confirm)) e.preventDefault();
  });
});

// Service price auto-fill from select
const svcSelect = document.getElementById('service_select');
const svcPrice = document.getElementById('service_price');
if (svcSelect && svcPrice) {
  svcSelect.addEventListener('change', function() {
    const opt = this.options[this.selectedIndex];
    if (opt.dataset.price) svcPrice.value = opt.dataset.price;
  });
}

// Part price auto-fill
const partSelect = document.getElementById('part_select');
const partPrice = document.getElementById('part_price');
if (partSelect && partPrice) {
  partSelect.addEventListener('change', function() {
    const opt = this.options[this.selectedIndex];
    if (opt.dataset.price) partPrice.value = opt.dataset.price;
  });
}
