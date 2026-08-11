/* ==========================================================================
   VentureAI — script.js
   Vanilla JS interactions only. No frameworks, no dependencies.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

  /* ---------------------------------------------------------
     1. Mobile hamburger menu
  --------------------------------------------------------- */
  const hamburger = document.getElementById('hamburger');
  const mobileNav = document.getElementById('mobile-nav');

  function closeMobileNav() {
    hamburger.classList.remove('open');
    mobileNav.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
  }

  if (hamburger && mobileNav) {
    hamburger.addEventListener('click', () => {
      const isOpen = mobileNav.classList.toggle('open');
      hamburger.classList.toggle('open', isOpen);
      hamburger.setAttribute('aria-expanded', String(isOpen));
    });

    mobileNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', closeMobileNav);
    });
  }

  /* ---------------------------------------------------------
     2. Smooth scrolling navigation (anchor links)
  --------------------------------------------------------- */
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId.length <= 1) return;
      const target = document.querySelector(targetId);
      if (!target) return;
      e.preventDefault();
      const navH = document.getElementById('navbar').offsetHeight;
      const top = target.getBoundingClientRect().top + window.pageYOffset - navH + 1;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  /* ---------------------------------------------------------
     3. Active navbar link based on scroll position
  --------------------------------------------------------- */
  const sections = document.querySelectorAll('main > section[id], .about[id]');
  const navLinks = document.querySelectorAll('.nav-link[data-nav]');

  function setActiveLink(id) {
    navLinks.forEach(link => {
      const match = link.getAttribute('href') === `#${id}`;
      link.classList.toggle('active', match);
    });
  }

  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        setActiveLink(entry.target.id);
      }
    });
  }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });

  sections.forEach(section => sectionObserver.observe(section));

  /* ---------------------------------------------------------
     4. Scroll reveal animations
  --------------------------------------------------------- */
  const revealEls = document.querySelectorAll('.reveal');
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  revealEls.forEach(el => revealObserver.observe(el));

  /* ---------------------------------------------------------
     5. Feature card hover — handled purely in CSS
     (transform + shadow on :hover). Nothing extra needed here.
  --------------------------------------------------------- */

  /* ---------------------------------------------------------
     6. Testimonial carousel
  --------------------------------------------------------- */
  const track = document.getElementById('testimonials-track');
  const dotsWrap = document.getElementById('testimonials-dots');

  if (track && dotsWrap) {
    const cards = Array.from(track.children);
    let activeIndex = 0;
    let autoTimer = null;

    cards.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.setAttribute('aria-label', `Show testimonial ${i + 1}`);
      if (i === 0) dot.classList.add('active');
      dot.addEventListener('click', () => goTo(i, true));
      dotsWrap.appendChild(dot);
    });

    const dots = Array.from(dotsWrap.children);

    function isCarouselMode() {
      return window.matchMedia('(max-width: 960px)').matches;
    }

    function updateCarouselDisplay() {
      if (isCarouselMode()) {
        dotsWrap.style.display = 'flex';
        cards.forEach((card, i) => {
          card.style.display = i === activeIndex ? 'block' : 'none';
        });
      } else {
        dotsWrap.style.display = 'none';
        cards.forEach(card => { card.style.display = 'block'; });
      }
    }

    function goTo(index, userTriggered) {
      activeIndex = (index + cards.length) % cards.length;
      dots.forEach((d, i) => d.classList.toggle('active', i === activeIndex));
      updateCarouselDisplay();
      if (userTriggered) restartAutoRotate();
    }

    function autoRotate() {
      if (isCarouselMode()) goTo(activeIndex + 1, false);
    }

    function restartAutoRotate() {
      clearInterval(autoTimer);
      autoTimer = setInterval(autoRotate, 5500);
    }

    updateCarouselDisplay();
    restartAutoRotate();
    window.addEventListener('resize', updateCarouselDisplay);
  }

  /* ---------------------------------------------------------
     7. Animated statistics counters
  --------------------------------------------------------- */
  const statNums = document.querySelectorAll('.stat__num');

  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimal || '0', 10);
    const suffix = el.dataset.suffix || '';
    const duration = 1600;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const value = target * eased;
      el.textContent = (decimals > 0 ? value.toFixed(decimals) : Math.floor(value).toLocaleString()) + suffix;
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = (decimals > 0 ? target.toFixed(decimals) : target.toLocaleString()) + suffix;
      }
    }
    requestAnimationFrame(tick);
  }

  const statsObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  statNums.forEach(el => statsObserver.observe(el));

  /* ---------------------------------------------------------
     8. Navbar background/shadow change on scroll
  --------------------------------------------------------- */
  const navbar = document.getElementById('navbar');
  function handleNavScroll() {
    navbar.classList.toggle('scrolled', window.scrollY > 12);
  }
  handleNavScroll();
  window.addEventListener('scroll', handleNavScroll, { passive: true });

  /* ---------------------------------------------------------
     9. Newsletter form validation
  --------------------------------------------------------- */
  const newsletterForm = document.getElementById('newsletter-form');
  const newsletterEmail = document.getElementById('newsletter-email');
  const newsletterMsg = document.getElementById('newsletter-msg');

  if (newsletterForm) {
    newsletterForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const value = newsletterEmail.value.trim();

      if (!value) {
        showNewsletterMsg('Please enter your email address.', 'error');
      } else if (!emailPattern.test(value)) {
        showNewsletterMsg('Please enter a valid email address.', 'error');
      } else {
        showNewsletterMsg("You're subscribed! Welcome aboard.", 'success');
        newsletterForm.reset();
      }
    });
  }

  function showNewsletterMsg(text, type) {
    newsletterMsg.textContent = text;
    newsletterMsg.className = `newsletter-msg ${type}`;
  }

  /* ---------------------------------------------------------
     10. Button click feedback (ripple effect)
  --------------------------------------------------------- */
  document.querySelectorAll('[data-ripple]').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const rect = this.getBoundingClientRect();
      const ripple = document.createElement('span');
      const size = Math.max(rect.width, rect.height);
      ripple.className = 'btn__ripple';
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
      this.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });

  /* ---------------------------------------------------------
     11. "See How It Works" smooth scroll target
     Falls back to the About section since there's no dedicated
     "How It Works" section on this page yet.
  --------------------------------------------------------- */
  const seeHowBtn = document.getElementById('see-how-it-works');
  if (seeHowBtn) {
    seeHowBtn.addEventListener('click', (e) => {
      const howItWorks = document.getElementById('how-it-works');
      if (!howItWorks) {
        e.preventDefault();
        const fallback = document.getElementById('about');
        const navH = navbar.offsetHeight;
        const top = fallback.getBoundingClientRect().top + window.pageYOffset - navH + 1;
        window.scrollTo({ top, behavior: 'smooth' });
      }
    });
  }

});
