/* ==========================================================================
   SIKUTAKI.AI — Interaction Enhancement Layer
   Menambah kenyamanan gerakan TANPA mengubah alur kerja/backend.
   Semua fitur bersifat additive, defensive (try/catch), dan non-blocking.
   ========================================================================== */
(function () {
    'use strict';

    var isTouch = window.matchMedia && window.matchMedia('(hover: none)').matches;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* ---------- 1. Page entrance ---------- */
    function markReady() {
        try { document.body.classList.add('siku-page-ready'); } catch (e) {}
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', markReady);
    } else {
        markReady();
    }

    /* ---------- 2. Reveal on scroll (staggered, agresif namun halus) ---------- */
    var revealIO = null;
    function tagAndObserveReveals() {
        if (reduceMotion || !revealIO) return;

        // Tag manual: [data-reveal]. Tag otomatis: blok section, kartu grid & bagian artikel.
        var targets = document.querySelectorAll(
            '[data-reveal], main > section > div, body > section > div, body > section .grid > *, main section .grid > *, main article > section, section[aria-label] > div, .siku-auto-reveal > *'
        );

        // Stagger per parent agar muncul berurutan
        var perParentCount = new Map();
        targets.forEach(function (el) {
            if (el.classList.contains('siku-reveal')) return;
            if (el.closest('[data-no-reveal]') || el.closest('[class*="marquee"]') || el.closest('#cursorGlow')) return;
            if (el.classList.contains('hidden') || el.closest('.hidden')) return;
            el.classList.add('siku-reveal');
            var p = el.parentElement;
            var idx = perParentCount.get(p) || 0;
            perParentCount.set(p, idx + 1);
            el.style.setProperty('--siku-delay', Math.min(idx * 0.08, 0.5) + 's');
            revealIO.observe(el);
        });
    }

    function setupReveal() {
        if (reduceMotion || !('IntersectionObserver' in window)) return;
        revealIO = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('siku-in');
                    revealIO.unobserve(entry.target);
                    // Nolkan delay setelah reveal agar hover tetap responsif
                    setTimeout(function () { entry.target.style.setProperty('--siku-delay', '0s'); }, 900);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -4% 0px' });

        tagAndObserveReveals();
        // Pass kedua: tangkap konten yang dirender dinamis setelah load (mis. grid blog)
        window.addEventListener('load', function () {
            setTimeout(tagAndObserveReveals, 400);
            setTimeout(tagAndObserveReveals, 1400);
        });
        // Pengaman: jika IO tidak sempat memicu (edge case), paksa tampil setelah 3 dtk
        setTimeout(function () {
            document.querySelectorAll('.siku-reveal:not(.siku-in)').forEach(function (el) {
                var r = el.getBoundingClientRect();
                if (r.top < window.innerHeight && r.bottom > 0) el.classList.add('siku-in');
            });
        }, 3000);
    }

    /* ---------- 3. Pointer glow tracking pada kartu ---------- */
    function setupGlow() {
        if (isTouch || reduceMotion) return;
        document.addEventListener('pointermove', function (e) {
            var card = e.target.closest && e.target.closest('.glow-card, [data-glow]');
            if (!card) return;
            var r = card.getBoundingClientRect();
            card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
            card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
        }, { passive: true });
    }

    /* ---------- 4. Tombol magnetik ---------- */
    function setupMagnetic() {
        if (isTouch || reduceMotion) return;
        document.querySelectorAll('[data-magnetic]').forEach(function (el) {
            var strength = parseFloat(el.getAttribute('data-magnetic')) || 0.25;
            el.addEventListener('pointermove', function (e) {
                var r = el.getBoundingClientRect();
                var x = (e.clientX - r.left - r.width / 2) * strength;
                var y = (e.clientY - r.top - r.height / 2) * strength;
                el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
            });
            el.addEventListener('pointerleave', function () {
                el.style.transform = '';
            });
        });
    }

    /* ---------- 5. Ripple pada CTA ---------- */
    function setupRipple() {
        if (reduceMotion) return;
        document.addEventListener('pointerdown', function (e) {
            var host = e.target.closest && e.target.closest('[data-ripple]');
            if (!host) return;
            try {
                host.classList.add('siku-ripple-host');
                var r = host.getBoundingClientRect();
                var d = Math.max(r.width, r.height);
                var s = document.createElement('span');
                s.className = 'siku-ripple';
                s.style.width = s.style.height = d + 'px';
                s.style.left = (e.clientX - r.left - d / 2) + 'px';
                s.style.top = (e.clientY - r.top - d / 2) + 'px';
                host.appendChild(s);
                setTimeout(function () { s.remove(); }, 700);
            } catch (err) {}
        }, { passive: true });
    }

    /* ---------- 6. Tilt halus untuk kartu unggulan ---------- */
    function setupTilt() {
        if (isTouch || reduceMotion) return;
        document.querySelectorAll('[data-tilt]').forEach(function (el) {
            var max = parseFloat(el.getAttribute('data-tilt')) || 6;
            el.style.transition = 'transform .35s cubic-bezier(.22,1,.36,1)';
            el.addEventListener('pointermove', function (e) {
                var r = el.getBoundingClientRect();
                var rx = ((e.clientY - r.top) / r.height - 0.5) * -max;
                var ry = ((e.clientX - r.left) / r.width - 0.5) * max;
                el.style.transform = 'perspective(800px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) translateY(-4px)';
            });
            el.addEventListener('pointerleave', function () { el.style.transform = ''; });
        });
    }

    /* ---------- 7. Toast helper global ---------- */
    window.sikuToast = function (msg, duration) {
        try {
            var t = document.createElement('div');
            t.className = 'siku-toast';
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(function () {
                t.style.transition = 'opacity .4s, transform .4s';
                t.style.opacity = '0';
                t.style.transform = 'translateX(-50%) translateY(8px)';
                setTimeout(function () { t.remove(); }, 420);
            }, duration || 2600);
        } catch (e) {}
    };

    /* ---------- 8. Init ---------- */
    function init() {
        try { setupReveal(); } catch (e) {}
        try { setupGlow(); } catch (e) {}
        try { setupMagnetic(); } catch (e) {}
        try { setupRipple(); } catch (e) {}
        try { setupTilt(); } catch (e) {}
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
