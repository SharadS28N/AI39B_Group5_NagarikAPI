/**
 * NagarikAPI — Global UI Scripts
 * Premium dark theme: navbar, mobile menu, scroll effects, reveal animations
 */

class NagarikUI {
  constructor() {
    this.navbar    = document.getElementById('ng-navbar');
    this.toggle    = document.getElementById('ng-nav-toggle');
    this.menu      = document.getElementById('ng-mobile-menu');
    this.iconMenu  = document.getElementById('icon-menu');
    this.iconClose = document.getElementById('icon-close');
    this.menuOpen  = false;

    this.init();
  }

  init() {
    this.initNavbarScroll();
    this.initMobileMenu();
    this.initReveal();
    this.initLucide();
  }

  /* ── Navbar: add .scrolled class on scroll ── */
  initNavbarScroll() {
    if (!this.navbar) return;
    const tick = () => {
      const scrolled = window.scrollY > 20;
      this.navbar.classList.toggle('scrolled', scrolled);
    };
    window.addEventListener('scroll', tick, { passive: true });
    tick();
  }

  /* ── Mobile Menu ── */
  initMobileMenu() {
    if (!this.toggle || !this.menu) return;

    this.toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      this.setMenu(!this.menuOpen);
    });

    // Close on any link inside menu
    this.menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => this.setMenu(false));
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (this.menuOpen && !this.menu.contains(e.target) && !this.toggle.contains(e.target)) {
        this.setMenu(false);
      }
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.menuOpen) this.setMenu(false);
    });

    // Close on resize above breakpoint
    window.addEventListener('resize', () => {
      if (window.innerWidth > 900 && this.menuOpen) this.setMenu(false);
    }, { passive: true });
  }

  setMenu(open) {
    this.menuOpen = open;
    this.menu.classList.toggle('is-open', open);
    this.toggle.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';

    if (this.iconMenu && this.iconClose) {
      this.iconMenu.style.display  = open ? 'none'  : 'block';
      this.iconClose.style.display = open ? 'block' : 'none';
    }
  }

  /* ── Scroll Reveal ── */
  initReveal() {
    const targets = document.querySelectorAll('[data-animate]');
    if (!targets.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    );

    targets.forEach((el, i) => {
      if (!el.style.getPropertyValue('--reveal-delay')) {
        el.style.setProperty('--reveal-delay', `${Math.min(i * 50, 350)}ms`);
      }
      observer.observe(el);
    });
  }

  /* ── Lucide Icons ── */
  initLucide() {
    if (window.lucide) window.lucide.createIcons();
  }
}

// Boot
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new NagarikUI());
} else {
  new NagarikUI();
}
