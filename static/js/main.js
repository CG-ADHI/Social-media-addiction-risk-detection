/* MindGuard v2 — Main JS */

// ── Animate stat counters on load ──────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    if (!target) return;
    let cur = 0;
    const step = Math.max(1, Math.ceil(target / 50));
    const t = setInterval(() => {
      cur = Math.min(cur + step, target);
      el.textContent = cur;
      if (cur >= target) clearInterval(t);
    }, 25);
  });
});

// ── Intersection observer for stagger animations ───
const io = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.style.animationPlayState = 'running'; });
}, { threshold: 0.1 });

document.querySelectorAll('.anim-in').forEach(el => {
  el.style.animationPlayState = 'paused';
  io.observe(el);
});

// ── Button ripple effect ───────────────────────────
document.addEventListener('click', e => {
  const btn = e.target.closest('.btn');
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const ripple = Object.assign(document.createElement('span'), {});
  ripple.style.cssText = `
    position:absolute;border-radius:50%;pointer-events:none;
    background:rgba(255,255,255,0.18);
    width:${size}px;height:${size}px;
    left:${e.clientX - rect.left - size/2}px;
    top:${e.clientY - rect.top - size/2}px;
    transform:scale(0);transition:transform 0.55s ease,opacity 0.55s;opacity:1;
  `;
  if (getComputedStyle(btn).position === 'static') btn.style.position = 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(ripple);
  requestAnimationFrame(() => { ripple.style.transform = 'scale(2.5)'; ripple.style.opacity = '0'; });
  setTimeout(() => ripple.remove(), 600);
});

// ── Screen-time slider color feedback ─────────────
const stSlider = document.getElementById('stSlider');
if (stSlider) {
  stSlider.addEventListener('input', function() {
    const v = parseFloat(this.value);
    const color = v > 6 ? 'var(--danger)' : v > 3 ? 'var(--warning)' : 'var(--lime)';
    document.getElementById('stVal').style.color = color;
  });
}

// ── Mood card bounce on select ────────────────────
document.querySelectorAll('.mood-opt').forEach(radio => {
  radio.addEventListener('change', function() {
    const lbl = document.querySelector(`label[for="${this.id}"]`);
    if (!lbl) return;
    lbl.style.transform = 'scale(1.08)';
    setTimeout(() => lbl.style.transform = '', 200);
  });
});

// ── Auto-resize textareas ─────────────────────────
document.querySelectorAll('textarea').forEach(ta => {
  ta.addEventListener('input', function() {
    if (this.id === 'chatInput') return; // handled separately
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
  });
});

// ── Global CSRF helper ────────────────────────────
window.getCsrf = () =>
  document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';

// ── Console branding ──────────────────────────────
console.log('%c🧠 MindGuard v2', 'color:#a3e635;font-size:1.4rem;font-weight:900;');
console.log('%cBiopunk wellness. Reclaim your mind.', 'color:#22d3ee;font-size:0.85rem;');
