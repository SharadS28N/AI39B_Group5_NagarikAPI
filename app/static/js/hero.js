(function () {
    const form = document.querySelector('.hero-cta');
    if (!form) {
        return;
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();

        const emailInput = form.querySelector('input[type="email"]');
        if (!emailInput) {
            return;
        }

        if (!emailInput.value.trim()) {
            emailInput.focus();
            return;
        }

        const button = form.querySelector('button[type="submit"]');
        if (!button) {
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Request Sent';

        window.setTimeout(function () {
            button.disabled = false;
            button.textContent = originalText;
        }, 1600);
    });
})();

const elements = document.querySelectorAll('a[href*="spline.design"]');
elements.forEach(el => el.remove());

document.addEventListener("DOMContentLoaded", function() {
  const elements = document.querySelectorAll('a, button, div, span');
  
  elements.forEach(function(el) {
    // Check if the element contains "Built with Spline" text
    if (el.innerText.includes("Built with Spline") || 
        el.innerText.includes("built with spline")) {
      el.remove();
      console.log("Removed Spline badge");
    }
  });
});