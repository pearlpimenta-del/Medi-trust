// Auto-hide toasts, confirm dialogs, and role-based register fields, dynamic medicine rows
document.querySelectorAll('.toast').forEach(t => setTimeout(() => t.remove(), 4000));
document.querySelectorAll('[data-confirm]').forEach(f => f.addEventListener('submit', e => {
  if (!confirm(f.dataset.confirm)) e.preventDefault();
}));
const role = document.getElementById('role');
if (role) {
  const toggle = () => {
    document.getElementById('doctorFields').style.display = role.value === 'doctor' ? 'block' : 'none';
    document.getElementById('patientFields').style.display = role.value === 'patient' ? 'block' : 'none';
  };
  role.addEventListener('change', toggle); toggle();
}
const reg = document.getElementById('regForm');
if (reg) reg.addEventListener('submit', e => {
  const p = reg.password.value;
  if (p.length < 6 || p !== reg.confirm.value) { e.preventDefault(); alert('Password must be 6+ characters and match confirmation'); }
});
function addMedicine() {
  const d = document.createElement('div'); d.className = 'row';
  d.innerHTML = '<input name="med_name" placeholder="Medicine"><input name="med_dose" placeholder="Dosage"><input name="med_freq" placeholder="Frequency"><input name="med_dur" placeholder="Duration"><button type="button" class="btn red sm" onclick="this.parentElement.remove()">Remove</button>';
  document.getElementById('meds').appendChild(d);
}
