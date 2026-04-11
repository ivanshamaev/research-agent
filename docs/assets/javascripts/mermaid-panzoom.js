(function () {
  let observerStarted = false;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function parseViewBox(svg) {
    const raw = svg.getAttribute("viewBox");
    if (raw) {
      const parts = raw.trim().split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts.every(Number.isFinite)) {
        return {
          x: parts[0],
          y: parts[1],
          width: parts[2],
          height: parts[3],
        };
      }
    }

    const box = svg.getBBox();
    const safeWidth = box.width || 100;
    const safeHeight = box.height || 100;
    const padX = Math.max(safeWidth * 0.05, 24);
    const padY = Math.max(safeHeight * 0.05, 24);

    return {
      x: box.x - padX,
      y: box.y - padY,
      width: safeWidth + padX * 2,
      height: safeHeight + padY * 2,
    };
  }

  function setViewBox(svg, box) {
    svg.setAttribute("viewBox", `${box.x} ${box.y} ${box.width} ${box.height}`);
  }

  function createButton(label, title, onClick) {
    const button = document.createElement("button");
    button.className = "mermaid-panzoom__button";
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-label", title);
    button.title = title;
    button.addEventListener("click", onClick);
    return button;
  }

  function setupDiagram(svg) {
    if (svg.dataset.panzoomReady === "true") {
      return;
    }

    const mermaidBlock = svg.closest(".mermaid");
    if (!mermaidBlock || !mermaidBlock.parentNode) {
      return;
    }

    const base = parseViewBox(svg);
    const ratio = base.height / base.width;
    const state = {
      base,
      current: { ...base },
      minWidth: base.width / 8,
      maxWidth: base.width,
      pointerId: null,
      dragStart: null,
    };

    const frame = document.createElement("div");
    frame.className = "mermaid-panzoom";

    const stage = document.createElement("div");
    stage.className = "mermaid-panzoom__stage";

    const controls = document.createElement("div");
    controls.className = "mermaid-panzoom__controls";

    const hint = document.createElement("div");
    hint.className = "mermaid-panzoom__hint";
    hint.textContent = "Wheel to zoom, drag to pan";

    mermaidBlock.parentNode.insertBefore(frame, mermaidBlock);
    frame.appendChild(stage);
    stage.appendChild(mermaidBlock);
    frame.appendChild(controls);
    frame.appendChild(hint);

    svg.dataset.panzoomReady = "true";
    mermaidBlock.dataset.panzoomWrapped = "true";
    svg.style.width = "100%";
    svg.style.height = "auto";
    svg.style.maxWidth = "none";
    setViewBox(svg, state.current);

    function update(box) {
      state.current = box;
      setViewBox(svg, box);
    }

    function reset() {
      update({ ...state.base });
    }

    function zoomAt(clientX, clientY, factor) {
      const rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return;
      }

      const nextWidth = clamp(state.current.width * factor, state.minWidth, state.maxWidth);
      const nextHeight = nextWidth * ratio;
      const px = (clientX - rect.left) / rect.width;
      const py = (clientY - rect.top) / rect.height;
      const focusX = state.current.x + state.current.width * px;
      const focusY = state.current.y + state.current.height * py;

      update({
        x: focusX - nextWidth * px,
        y: focusY - nextHeight * py,
        width: nextWidth,
        height: nextHeight,
      });
    }

    function zoomFromCenter(factor) {
      const rect = stage.getBoundingClientRect();
      zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
    }

    controls.appendChild(createButton("+", "Zoom in", function () {
      zoomFromCenter(1 / 1.2);
    }));
    controls.appendChild(createButton("-", "Zoom out", function () {
      zoomFromCenter(1.2);
    }));
    controls.appendChild(createButton("Reset", "Reset diagram view", reset));

    stage.addEventListener("wheel", function (event) {
      event.preventDefault();
      zoomAt(event.clientX, event.clientY, event.deltaY < 0 ? 1 / 1.15 : 1.15);
    }, { passive: false });

    stage.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) {
        return;
      }

      state.pointerId = event.pointerId;
      state.dragStart = {
        clientX: event.clientX,
        clientY: event.clientY,
        viewBox: { ...state.current },
      };
      stage.classList.add("is-dragging");
      stage.setPointerCapture(event.pointerId);
      event.preventDefault();
    });

    stage.addEventListener("pointermove", function (event) {
      if (state.pointerId !== event.pointerId || !state.dragStart) {
        return;
      }

      const rect = stage.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return;
      }

      const scaleX = state.dragStart.viewBox.width / rect.width;
      const scaleY = state.dragStart.viewBox.height / rect.height;
      const deltaX = (event.clientX - state.dragStart.clientX) * scaleX;
      const deltaY = (event.clientY - state.dragStart.clientY) * scaleY;

      update({
        x: state.dragStart.viewBox.x - deltaX,
        y: state.dragStart.viewBox.y - deltaY,
        width: state.dragStart.viewBox.width,
        height: state.dragStart.viewBox.height,
      });
    });

    function stopDrag(event) {
      if (state.pointerId !== event.pointerId) {
        return;
      }

      state.pointerId = null;
      state.dragStart = null;
      stage.classList.remove("is-dragging");
      if (stage.hasPointerCapture(event.pointerId)) {
        stage.releasePointerCapture(event.pointerId);
      }
    }

    stage.addEventListener("pointerup", stopDrag);
    stage.addEventListener("pointercancel", stopDrag);
    stage.addEventListener("dblclick", reset);
  }

  function scan(root) {
    root.querySelectorAll(".mermaid svg").forEach(setupDiagram);
  }

  function startObserver() {
    if (observerStarted || !document.body) {
      return;
    }

    observerStarted = true;
    const observer = new MutationObserver(function () {
      window.requestAnimationFrame(function () {
        scan(document);
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  function boot() {
    startObserver();
    scan(document);
    window.setTimeout(function () {
      scan(document);
    }, 300);
    window.setTimeout(function () {
      scan(document);
    }, 1000);
  }

  document.addEventListener("DOMContentLoaded", boot);

  if (typeof window.document$ !== "undefined" && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(boot);
  }
})();
