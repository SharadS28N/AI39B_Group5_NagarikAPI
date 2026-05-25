(function () {
  function scrollToElement(selector) {
    const element = document.querySelector(selector);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function debounce(func, delay) {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  }

  function throttle(func, delay) {
    let lastCalled = 0;
    return (...args) => {
      const now = Date.now();
      if (now - lastCalled >= delay) {
        func(...args);
        lastCalled = now;
      }
    };
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function isElementInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
      rect.top <= (window.innerHeight || document.documentElement.clientHeight) &&
      rect.left <= (window.innerWidth || document.documentElement.clientWidth) &&
      rect.bottom >= 0 &&
      rect.right >= 0
    );
  }

  window.ngUtils = {
    scrollToElement,
    debounce,
    throttle,
    prefersReducedMotion,
    isElementInViewport
  };
})();
