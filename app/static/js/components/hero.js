class HeroComponent {
  constructor() {
    this.form = document.querySelector(".ng-demo-form");
    this.emailInput = document.querySelector("#ng-demo-email");
    this.submitBtn = this.form ? this.form.querySelector("button[type='submit']") : null;
    this.mobileToggle = document.querySelector("#mobile-menu-btn");
    this.mobileMenu = document.querySelector("#mobile-menu");


    if (this.form && this.emailInput && this.submitBtn) {
      this.form.addEventListener("submit", (event) => this.handleSubmit(event));
    }
  }


  async handleSubmit(event) {
    event.preventDefault();
    const email = this.emailInput.value.trim();

    if (!this.validateEmail(email)) {
      this.showNotification("Please enter a valid work email.", "error");
      this.emailInput.focus();
      return;
    }

    this.setLoading(true);

    try {
      const response = await fetch(this.form.action, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      if (!response.ok) {
        throw new Error("Request failed");
      }

      this.showNotification("Request sent successfully.", "success");
      this.form.reset();
    } catch (error) {
      console.error("Demo request error:", error);
      this.showNotification("Could not send request right now. Please try again.", "error");
    } finally {
      this.setLoading(false);
    }
  }

  validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  setLoading(isLoading) {
    if (!this.submitBtn) {
      return;
    }

    this.submitBtn.disabled = isLoading;
    this.submitBtn.textContent = isLoading ? "Sending..." : "Book demo";
    this.submitBtn.style.opacity = isLoading ? "0.75" : "1";
  }

  showNotification(message, type) {
    const notification = document.createElement("div");
    notification.className = "ng-toast";
    notification.style.cssText = [
      "position: fixed",
      "right: 16px",
      "bottom: 16px",
      "padding: 12px 14px",
      "border-radius: 10px",
      "font-size: 13px",
      "font-weight: 600",
      "z-index: 1200",
      "color: #ffffff",
      `background: ${type === "success" ? "#16a34a" : "#dc2626"}`,
      "box-shadow: 0 12px 22px rgba(0, 0, 0, 0.2)"
    ].join(";");
    notification.textContent = message;
    document.body.appendChild(notification);

    window.setTimeout(() => {
      notification.remove();
    }, 2600);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => new HeroComponent());
} else {
  new HeroComponent();
}
