# Nagarik API

Nagarik API is a Flask + Jinja identity-verification starter that combines a clean server-rendered architecture with a modern frontend experience. It includes a Next.js-style landing page and an optional React island for interactive UI components.

---

## Overview

This project demonstrates how to integrate a Python backend with a modern JavaScript-driven UI while keeping server-side rendering as the foundation. It is designed to be simple, extensible, and production-aware.

---

## Core Stack

* Backend: Python, Flask
* Templating: Jinja2
* Frontend: HTML, CSS, JavaScript
* Design: Tailwind CSS (CDN) with a custom design system
* Icons: Lucide
* Optional UI Layer: React, Radix UI, Framer Motion

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-111111?style=for-the-badge\&logo=flask\&logoColor=white)
![Jinja](https://img.shields.io/badge/Jinja-B41717?style=for-the-badge\&logo=jinja\&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge\&logo=javascript\&logoColor=111111)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge\&logo=html5\&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge\&logo=css3\&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge\&logo=tailwindcss\&logoColor=white)
![Lucide](https://img.shields.io/badge/Lucide-0f172a?style=for-the-badge\&logo=lucide\&logoColor=white)
![React](https://img.shields.io/badge/React-149ECA?style=for-the-badge\&logo=react\&logoColor=white)
![Radix UI](https://img.shields.io/badge/Radix_UI-161618?style=for-the-badge\&logo=radixui\&logoColor=white)
![Framer Motion](https://img.shields.io/badge/Framer_Motion-0055FF?style=for-the-badge\&logo=framer\&logoColor=white)

---

## Architecture

* Flask routes render Jinja templates as the primary view layer
* Layouts, pages, and reusable components structure the UI
* Styling is handled through design tokens and global styles
* JavaScript enhances interactivity where required
* A React island can be mounted into a single DOM node when needed

---

## Project Structure

```text
AI39B_Group5_NagarikAPI/
├─ app/
│  ├─ __init__.py
│  ├─ routes/
│  │  └─ views.py
│  ├─ static/
│  │  ├─ css/
│  │  │  ├─ tokens.css
│  │  │  ├─ globals.css
│  │  │  ├─ animations.css
│  │  │  └─ hero.css
│  │  └─ js/
│  │     ├─ utils.js
│  │     └─ components/
│  │        ├─ hero.js
│  │        └─ react-island.js
│  └─ templates/
│     ├─ layouts/
│     │  └─ base.html
│     ├─ pages/
│     │  └─ index.html
│     └─ components/
│        ├─ navbar/
│        │  └─ header.html
│        ├─ hero/
│        │  └─ hero-section.html
│        └─ footer/
│           └─ footer.html
├─ config.py
├─ requirements.txt
├─ run.py
└─ README.md
```

---

## Features

* Responsive navigation with mobile support
* Full landing page with hero section and demo request form
* Feature and compliance sections
* Stack visualization
* Optional React-powered interactive components
* Fully responsive layout across devices

---

## React Island

This project includes an optional React island embedded within a Jinja-rendered page.

How it works:

1. Jinja renders a mount node inside the template
2. The page loads a JavaScript module for the island
3. React initializes only if the mount node exists
4. Interactive components (Radix UI, Framer Motion) run inside that scope

This approach keeps the core system lightweight while allowing modern UI enhancements.

---

## Access Roles and Authentication

| Role            | Interface    | Description                                | Default Credentials                                            |
| --------------- | ------------ | ------------------------------------------ | -------------------------------------------------------------- |
| Superuser Admin | `/dashboard` | System-wide control and monitoring         | [admin@nagarikapi.com](mailto:admin@nagarikapi.com) / Admin123 |
| Company Admin   | `/dashboard` | Organization-level management              | [hr@banknepal.com](mailto:hr@banknepal.com) / CompanyAdmin123  |
| End User        | `/dashboard` | Personal identity and verification control | [user@example.com](mailto:user@example.com) / User123          |

### Authentication Flow

1. Users register via `/register`
2. Organizations request onboarding via demo flow
3. Admin assigns company roles
4. Users complete KYC verification and share results securely

---

## Design System

The interface follows a dark, minimal design system:

* Background: `#050505`
* Accent: `#8b5cf6`
* Surface: translucent with blur effects
* Typography: Space Grotesk and Inter

---

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Environment Variables

```text
SECRET_KEY=your_secure_random_string
SQLALCHEMY_DATABASE_URI=mysql+pymysql://user:pass@host/dbname
```

### Database Migration

```bash
flask db migrate -m "initial"
flask db upgrade
```

### Run Application

```bash
python run.py
```

---

## Notes

* Database SSL CA path is configured in `config.py`
* React island uses CDN-based ES modules (no build step required)
* For production, consider bundling with Vite

---

## Contributors

<div align="center">

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/SharadS28N">
        <img src="https://github.com/SharadS28N.png" width="100px;" style="border-radius:50%;" alt="SharadS28N"/><br />
        <sub><b>Sharad Bhandari</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/sushant-malla">
        <img src="https://github.com/sushant-malla.png" width="100px;" style="border-radius:50%;" alt="sushant-malla"/><br />
        <sub><b>Mingmar Lama</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/mingmarlama">
        <img src="https://github.com/mingmarlama.png" width="100px;" style="border-radius:50%;" alt="mingmarlama"/><br />
        <sub><b>Mingmar Lama</b></sub>
      </a>
    </td>
  </tr>
</table>

</div>

---

## License

This project is intended for academic and educational use. Add a proper license if distributing publicly.
