(function () {
  let observerStarted = false;

  /* ── helpers ──────────────────────────────────────────────── */

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function parseViewBox(svg) {
    const raw = svg.getAttribute("viewBox");
    if (raw) {
      const parts = raw.trim().split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts.every(Number.isFinite)) {
        return { x: parts[0], y: parts[1], width: parts[2], height: parts[3] };
      }
    }
    const box = svg.getBBox();
    const w = box.width  || 100;
    const h = box.height || 100;
    const px = Math.max(w * 0.05, 24);
    const py = Math.max(h * 0.05, 24);
    return { x: box.x - px, y: box.y - py, width: w + px * 2, height: h + py * 2 };
  }

  function setViewBox(svg, box) {
    svg.setAttribute("viewBox", `${box.x} ${box.y} ${box.width} ${box.height}`);
  }

  function createButton(label, title, onClick) {
    const btn = document.createElement("button");
    btn.className = "mermaid-panzoom__button";
    btn.type = "button";
    btn.textContent = label;
    btn.setAttribute("aria-label", title);
    btn.title = title;
    btn.addEventListener("click", onClick);
    return btn;
  }

  /* ── core pan/zoom logic (works on any stage + svg pair) ──── */

  function attachPanZoom(stage, svg, opts) {
    opts = opts || {};
    const base    = parseViewBox(svg);
    const ratio   = base.height / base.width;
    const state   = {
      base,
      current:   { ...base },
      minWidth:  base.width / 8,
      maxWidth:  base.width * (opts.maxZoomOut || 1),
      pointerId: null,
      dragStart: null,
    };

    svg.style.width    = "100%";
    svg.style.height   = "auto";
    svg.style.maxWidth = "none";
    setViewBox(svg, state.current);

    function update(box) {
      state.current = box;
      setViewBox(svg, box);
    }

    function reset() { update({ ...state.base }); }

    function zoomAt(clientX, clientY, factor) {
      const rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const next  = clamp(state.current.width * factor, state.minWidth, state.maxWidth);
      const nextH = next * ratio;
      const px = (clientX - rect.left)  / rect.width;
      const py = (clientY - rect.top)   / rect.height;
      const fx = state.current.x + state.current.width  * px;
      const fy = state.current.y + state.current.height * py;
      update({ x: fx - next * px, y: fy - nextH * py, width: next, height: nextH });
    }

    function zoomCenter(factor) {
      const r = stage.getBoundingClientRect();
      zoomAt(r.left + r.width / 2, r.top + r.height / 2, factor);
    }

    stage.addEventListener("wheel", function (e) {
      e.preventDefault();
      zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 1 / 1.15 : 1.15);
    }, { passive: false });

    stage.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      state.pointerId = e.pointerId;
      state.dragStart = { clientX: e.clientX, clientY: e.clientY, viewBox: { ...state.current } };
      stage.classList.add("is-dragging");
      stage.setPointerCapture(e.pointerId);
      e.preventDefault();
    });

    stage.addEventListener("pointermove", function (e) {
      if (state.pointerId !== e.pointerId || !state.dragStart) return;
      const rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const sx = state.dragStart.viewBox.width  / rect.width;
      const sy = state.dragStart.viewBox.height / rect.height;
      update({
        x: state.dragStart.viewBox.x - (e.clientX - state.dragStart.clientX) * sx,
        y: state.dragStart.viewBox.y - (e.clientY - state.dragStart.clientY) * sy,
        width:  state.dragStart.viewBox.width,
        height: state.dragStart.viewBox.height,
      });
    });

    function stopDrag(e) {
      if (state.pointerId !== e.pointerId) return;
      state.pointerId = null;
      state.dragStart = null;
      stage.classList.remove("is-dragging");
      if (stage.hasPointerCapture(e.pointerId)) stage.releasePointerCapture(e.pointerId);
    }

    stage.addEventListener("pointerup",     stopDrag);
    stage.addEventListener("pointercancel", stopDrag);
    stage.addEventListener("dblclick",      reset);

    return { zoomCenter, reset };
  }

  /* ── fullscreen overlay ───────────────────────────────────── */

  function openFullscreen(sourceSvg) {
    const overlay = document.createElement("div");
    overlay.className = "mermaid-panzoom__overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    const inner = document.createElement("div");
    inner.className = "mermaid-panzoom__overlay-inner";

    const stage = document.createElement("div");
    stage.className = "mermaid-panzoom__overlay-stage";

    /* clone svg so original stays intact */
    const svgClone = sourceSvg.cloneNode(true);
    delete svgClone.dataset.panzoomReady;
    stage.appendChild(svgClone);

    const controls = document.createElement("div");
    controls.className = "mermaid-panzoom__controls";

    inner.appendChild(stage);
    inner.appendChild(controls);
    overlay.appendChild(inner);
    document.body.appendChild(overlay);

    /* attach pan/zoom with wider zoom-out limit for fullscreen */
    const pz = attachPanZoom(stage, svgClone, { maxZoomOut: 3 });

    controls.appendChild(createButton("+",     "Zoom in",           function () { pz.zoomCenter(1 / 1.2); }));
    controls.appendChild(createButton("−",     "Zoom out",          function () { pz.zoomCenter(1.2);     }));
    controls.appendChild(createButton("Reset", "Reset view",        pz.reset));
    controls.appendChild(createButton("✕",     "Close fullscreen",  close));

    const hint = document.createElement("div");
    hint.className = "mermaid-panzoom__hint";
    hint.textContent = "Wheel — zoom · Drag — pan · Dbl-click — reset · Esc — close";
    inner.appendChild(hint);

    function close() {
      document.body.removeChild(overlay);
      document.removeEventListener("keydown", onKey);
    }

    function onKey(e) {
      if (e.key === "Escape") close();
    }

    document.addEventListener("keydown", onKey);

    /* click on dark backdrop closes */
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
  }

  /* ── inline diagram setup ─────────────────────────────────── */

  function setupDiagram(svg) {
    if (svg.dataset.panzoomReady === "true") return;

    const mermaidBlock = svg.closest(".mermaid");
    if (!mermaidBlock || !mermaidBlock.parentNode) return;

    const frame = document.createElement("div");
    frame.className = "mermaid-panzoom";

    const stage = document.createElement("div");
    stage.className = "mermaid-panzoom__stage";

    const controls = document.createElement("div");
    controls.className = "mermaid-panzoom__controls";

    const hint = document.createElement("div");
    hint.className = "mermaid-panzoom__hint";
    hint.textContent = "Wheel — zoom · Drag — pan · Dbl-click — reset";

    mermaidBlock.parentNode.insertBefore(frame, mermaidBlock);
    frame.appendChild(stage);
    stage.appendChild(mermaidBlock);
    frame.appendChild(controls);
    frame.appendChild(hint);

    svg.dataset.panzoomReady = "true";
    mermaidBlock.dataset.panzoomWrapped = "true";

    const pz = attachPanZoom(stage, svg);

    controls.appendChild(createButton("+",     "Zoom in",        function () { pz.zoomCenter(1 / 1.2); }));
    controls.appendChild(createButton("−",     "Zoom out",       function () { pz.zoomCenter(1.2);     }));
    controls.appendChild(createButton("Reset", "Reset view",     pz.reset));
    controls.appendChild(createButton("⛶",    "Open fullscreen", function () { openFullscreen(svg);    }));
  }

  /* ── observer + boot ──────────────────────────────────────── */

  function scan(root) {
    root.querySelectorAll(".mermaid svg").forEach(setupDiagram);
  }

  function startObserver() {
    if (observerStarted || !document.body) return;
    observerStarted = true;
    const observer = new MutationObserver(function () {
      window.requestAnimationFrame(function () { scan(document); });
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-processed"] });
  }

  function boot() {
    startObserver();
    scan(document);
    window.setTimeout(function () { scan(document); }, 300);
    window.setTimeout(function () { scan(document); }, 1000);
    window.setTimeout(function () { scan(document); }, 3000);
  }

  /* ── boot ────────────────────────────────────────────────── */

  function initMermaid() {
    if (typeof window.mermaid === "undefined") return;
    window.mermaid.initialize({ startOnLoad: false, theme: "default" });
    var nodes = document.querySelectorAll(".mermaid:not([data-processed])");
    if (nodes.length) {
      window.mermaid.run({ nodes: Array.from(nodes) });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMermaid();
    boot();
  });

  if (typeof window.document$ !== "undefined" && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(function () {
      initMermaid();
      boot();
    });
  }
})();
