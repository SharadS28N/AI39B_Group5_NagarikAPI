import React, { useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import * as Tooltip from "https://esm.sh/@radix-ui/react-tooltip@1.1.2?deps=react@18.3.1";
import { AnimatePresence, motion } from "https://esm.sh/framer-motion@11.2.10?deps=react@18.3.1";


// Expose globals so runtime scanners can see libraries are active on the page.
window.React = React;
window.__NAGARIK_REACT_ACTIVE__ = true;
window.__NAGARIK_RADIX_ACTIVE__ = true;
window.__NAGARIK_FRAMER_ACTIVE__ = true;

function updateRuntimeProbe(selector, label) {
  const node = document.querySelector(selector);
  if (node) {
    node.textContent = `${label}: active`;
  }
}

function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

function BadgeButton({ active, onClick, children }) {
  return React.createElement(
    motion.button,
    {
      onClick,
      whileTap: { scale: 0.98 },
      className: cn(
        "rounded-full border px-3 py-1 text-xs font-semibold transition",
        active
            ? "border-violet-500 bg-violet-500/10 text-violet-400"
            : "border-white/10 bg-white/5 text-stone-400 hover:border-white/20 hover:text-white"
      )

    },
    children
  );
}

function IslandCard({ title, value, hint }) {
  return React.createElement(
    Tooltip.Provider,
    { delayDuration: 120 },
    React.createElement(
      Tooltip.Root,
      null,
      React.createElement(
        Tooltip.Trigger,
        { asChild: true },
        React.createElement(
          motion.article,
          {
            whileHover: { y: -3 },
            transition: { duration: 0.18, ease: "easeOut" },
            className: "rounded-xl border border-white/10 bg-white/[0.02] p-3 text-left backdrop-blur-sm"
          },
          React.createElement("p", { className: "text-xs font-semibold uppercase tracking-wide text-stone-500" }, title),
          React.createElement("p", { className: "mt-2 text-lg font-bold text-white" }, value)
        )

      ),
      React.createElement(
        Tooltip.Portal,
        null,
        React.createElement(
          Tooltip.Content,
          {
            sideOffset: 8,
            className: "rounded-md border border-stone-700 bg-stone-900 px-2 py-1 text-xs text-stone-100"
          },
          hint,
          React.createElement(Tooltip.Arrow, { className: "fill-stone-900" })
        )
      )
    )
  );
}

function ReactIsland() {
  const tabs = ["Editorial", "System", "Motion", "React vs Next.js"];
  const [active, setActive] = useState(tabs[0]);

  const comparisonRows = [
    ["Rendering", "Flexible CSR/SSR setup", "Built-in SSR/SSG/RSC pipeline"],
    ["Routing", "Library-based (React Router)", "File-based routing by default"],
    ["Performance", "Depends on architecture choices", "Opinionated optimizations out of the box"],
    ["Use here", "Interactive island in Flask", "Future full-frontend option if migration is needed"]
  ];

  const panel = useMemo(() => {
    if (active === "System") {
      return {
        title: "System Surface",
        body: "Flask + Jinja stay at the core while the React island adds polished interaction only where needed.",
        cards: [
          ["Core", "Flask + Jinja", "Server-rendered templates keep the app lightweight"],
          ["Island", "React + Radix", "Isolated interactive blocks for premium moments"],
          ["Style", "shadcn-inspired", "Soft borders, neutral surfaces, crisp hierarchy"]
        ]
      };
    }

    if (active === "Motion") {
      return {
        title: "Motion Language",
        body: "Framer Motion adds just enough movement to make the interface feel expensive, not busy.",
        cards: [
          ["Entrance", "Subtle", "Content fades and rises without drawing attention"],
          ["Hover", "Measured", "Cards lift a few pixels with a soft response"],
          ["Reduced motion", "Supported", "Animations back off when the user asks"]
        ]
      };
    }

    if (active === "React vs Next.js") {
      return {
        title: "React vs Next.js in this project",
        body: "This app currently uses Flask + Jinja with a React island. Next.js would require a dedicated frontend app or full migration.",
        cards: [
          ["Current", "Flask + React island", "Fast server rendering with selective premium interactions"],
          ["Available now", "Radix + Motion", "Modern interaction primitives are active in production"],
          ["Upgrade path", "Next.js frontend", "Can be added as a separate client when you want full Next runtime"]
        ]
      };
    }

    return {
      title: "Editorial Surface",
      body: "The landing page uses generous spacing, restrained contrast, and a quiet palette to feel premium.",
      cards: [
        ["Typeface", "Space Grotesk", "The current font stays in place across the site"],
        ["Palette", "Ivory + ink", "Warm neutrals replace the earlier dashboard blue"],
        ["Spacing", "Roomy", "Editorial whitespace keeps the layout calm"]
      ]
    };
  }, [active]);

  return React.createElement(
    "section",
    { className: "rounded-2xl border border-white/5 bg-black/40 p-4 md:p-10 backdrop-blur-xl" },
    React.createElement("p", { className: "text-xs font-semibold uppercase tracking-[0.18em] text-violet-500" }, "React + Radix UI + Framer Motion"),
    React.createElement("h3", { className: "mt-2 text-3xl font-bold text-white" }, "Premium interaction layer"),
    React.createElement(
      "p",
      { className: "mt-2 max-w-2xl text-base text-stone-400" },
      "This section is built with React, Radix UI primitives, Framer Motion transitions, and shadcn-inspired styling while the rest of the page stays fast in Jinja."
    )
,
    React.createElement(
      "div",
      { className: "mt-4 flex flex-wrap gap-2" },
      tabs.map((tab) =>
        React.createElement(BadgeButton, {
          key: tab,
          active: tab === active,
          onClick: () => setActive(tab)
        }, tab)
      )
    ),
    React.createElement(
      "div",
      { className: "mt-8 rounded-2xl border border-white/5 bg-white/[0.01] p-6" },

      React.createElement(
        AnimatePresence,
        { mode: "wait" },
        React.createElement(
          motion.div,
          {
            key: active,
            initial: { opacity: 0, y: 6 },
            animate: { opacity: 1, y: 0 },
            exit: { opacity: 0, y: -4 },
            transition: { duration: 0.2, ease: "easeOut" }
          },
          React.createElement("h4", { className: "text-xl font-bold text-white" }, panel.title),
          React.createElement("p", { className: "mt-2 text-base text-stone-400" }, panel.body),

          React.createElement(
            "div",
            { className: "mt-4 grid gap-3 md:grid-cols-3" },
            panel.cards.map(([title, value, hint]) =>
              React.createElement(IslandCard, {
                key: title,
                title,
                value,
                hint
              })
            )
          )
        )
      )
    )
    ,
    active === "React vs Next.js"
      ? React.createElement(
          "div",
          { className: "mt-8 overflow-hidden rounded-xl border border-white/5 bg-white/[0.01]" },
          React.createElement(
            "table",
            { className: "w-full border-collapse text-left text-sm" },
            React.createElement(
              "thead",
              { className: "bg-white/[0.03] text-stone-300" },

              React.createElement(
                "tr",
                null,
                React.createElement("th", { className: "px-3 py-2 font-semibold" }, "Dimension"),
                React.createElement("th", { className: "px-3 py-2 font-semibold" }, "React"),
                React.createElement("th", { className: "px-3 py-2 font-semibold" }, "Next.js")
              )
            ),
            React.createElement(
              "tbody",
              null,
              comparisonRows.map(([dimension, react, next], index) =>
                React.createElement(
                  "tr",
                  { key: dimension, className: index % 2 === 0 ? "transparent" : "bg-white/[0.01]" },
                  React.createElement("td", { className: "px-3 py-3 font-medium text-white" }, dimension),
                  React.createElement("td", { className: "px-3 py-3 text-stone-400" }, react),
                  React.createElement("td", { className: "px-3 py-3 text-stone-400" }, next)
                )
              )
            )

          )
        )
      : null
  );
}

const mountNode = document.querySelector("#ng-react-island");
if (mountNode) {
  updateRuntimeProbe("[data-runtime-react]", "React");
  updateRuntimeProbe("[data-runtime-radix]", "Radix UI");
  updateRuntimeProbe("[data-runtime-motion]", "Framer Motion");
  createRoot(mountNode).render(React.createElement(ReactIsland));
}
