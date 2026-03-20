const elements = {
  form: document.querySelector("#simulation-form"),
  functionInput: document.querySelector("#function-input"),
  exactInput: document.querySelector("#exact-input"),
  methodSelect: document.querySelector("#method-select"),
  t0Input: document.querySelector("#t0-input"),
  y0Input: document.querySelector("#y0-input"),
  hInput: document.querySelector("#h-input"),
  stepsInput: document.querySelector("#steps-input"),
  refinementInput: document.querySelector("#refinement-input"),
  formStatus: document.querySelector("#form-status"),
  methodPill: document.querySelector("#method-pill"),
  referencePill: document.querySelector("#reference-pill"),
  finalValue: document.querySelector("#final-value"),
  finalError: document.querySelector("#final-error"),
  maxError: document.querySelector("#max-error"),
  phaseTitle: document.querySelector("#phase-title"),
  phaseDescription: document.querySelector("#phase-description"),
  phaseFormula: document.querySelector("#phase-formula"),
  overlayStep: document.querySelector("#overlay-step"),
  overlaySpeed: document.querySelector("#overlay-speed"),
  playToggle: document.querySelector("#play-toggle"),
  restartButton: document.querySelector("#restart-button"),
  speedInput: document.querySelector("#speed-input"),
  canvas: document.querySelector("#scene"),
  presetButtons: document.querySelectorAll("[data-preset]"),
};

const state = {
  methods: [],
  simulation: null,
  phaseIndex: 0,
  phaseProgress: 0,
  playing: true,
  speed: 1.0,
  lastFrameTime: 0,
};

const presets = {
  classic: {
    function: "y - t**2 + 1",
    exact_function: "(t + 1)**2 - 0.5 * exp(t)",
    method: "rk4",
    t0: 0,
    y0: 0.5,
    h: 0.2,
    steps: 10,
    refinement: 40,
  },
  decay: {
    function: "-1.8 * y + sin(2*t)",
    exact_function: "",
    method: "heun",
    t0: 0,
    y0: 1,
    h: 0.18,
    steps: 22,
    refinement: 45,
  },
  oscillation: {
    function: "cos(t) - 0.4*y",
    exact_function: "",
    method: "midpoint",
    t0: 0,
    y0: 0,
    h: 0.22,
    steps: 24,
    refinement: 50,
  },
};

function fmt(value) {
  return Number(value).toPrecision(6).replace(/\.?0+$/, "");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(start, end, ratio) {
  return start + (end - start) * ratio;
}

function lerpPoint(start, end, ratio) {
  return {
    t: lerp(start.t, end.t, ratio),
    y: lerp(start.y, end.y, ratio),
  };
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "");
  return {
    r: Number.parseInt(clean.slice(0, 2), 16),
    g: Number.parseInt(clean.slice(2, 4), 16),
    b: Number.parseInt(clean.slice(4, 6), 16),
  };
}

function mixColor(first, second, ratio) {
  const a = hexToRgb(first);
  const b = hexToRgb(second);
  const safeRatio = clamp(ratio, 0, 1);
  const mix = (left, right) => Math.round(left + (right - left) * safeRatio);
  return `rgb(${mix(a.r, b.r)}, ${mix(a.g, b.g)}, ${mix(a.b, b.b)})`;
}

function phaseCountLabel() {
  if (!state.simulation) {
    return "Steg -";
  }
  return `Fase ${state.phaseIndex + 1}/${state.simulation.phases.length}`;
}

function currentPhase() {
  if (!state.simulation) {
    return null;
  }
  return state.simulation.phases[state.phaseIndex];
}

function currentStep() {
  const phase = currentPhase();
  if (!phase) {
    return null;
  }
  return state.simulation.trace.steps[phase.step_index];
}

function updateInfoPanel() {
  const simulation = state.simulation;
  if (!simulation) {
    elements.phaseTitle.textContent = "Ingen simulering enda";
    elements.phaseDescription.textContent = "Skriv inn et problem og start animasjonen.";
    elements.phaseFormula.textContent = "Formelen for den aktive fasen vises her.";
    elements.overlayStep.textContent = "Steg -";
    elements.overlaySpeed.textContent = `${state.speed.toFixed(1)}x`;
    elements.methodPill.textContent = "Metode";
    elements.referencePill.textContent = "Referanse";
    elements.finalValue.textContent = "-";
    elements.finalError.textContent = "-";
    elements.maxError.textContent = "-";
    return;
  }

  const phase = currentPhase();
  const step = currentStep();
  elements.phaseTitle.textContent = phase.title;
  elements.phaseDescription.textContent =
    phase.kind === "advance" && step
      ? `${phase.description} Lokal feil ved dette punktet er ${fmt(step.error)} mot ${simulation.summary.reference_label.toLowerCase()}.`
      : phase.description;
  elements.phaseFormula.textContent = phase.formula;
  elements.overlayStep.textContent = `${phaseCountLabel()} / steg ${phase.step_index + 1}`;
  elements.overlaySpeed.textContent = `${state.speed.toFixed(1)}x`;
  elements.methodPill.textContent = simulation.method.name;
  elements.referencePill.textContent = simulation.summary.reference_label;
  elements.finalValue.textContent = fmt(simulation.summary.final_value);
  elements.finalError.textContent = fmt(simulation.summary.final_error);
  elements.maxError.textContent = fmt(simulation.summary.max_error);
}

function collectFormPayload() {
  return {
    function: elements.functionInput.value,
    exact_function: elements.exactInput.value,
    method: elements.methodSelect.value,
    t0: Number(elements.t0Input.value),
    y0: Number(elements.y0Input.value),
    h: Number(elements.hInput.value),
    steps: Number(elements.stepsInput.value),
    refinement: Number(elements.refinementInput.value),
  };
}

async function loadMethods() {
  const response = await fetch("/api/methods");
  const payload = await response.json();
  state.methods = payload.methods;
  elements.methodSelect.innerHTML = payload.methods
    .map(
      (method) =>
        `<option value="${method.key}">${method.name}</option>`
    )
    .join("");
  elements.methodSelect.value = "rk4";
}

async function simulate(event) {
  if (event) {
    event.preventDefault();
  }
  elements.formStatus.textContent = "Kjorer simulering...";

  const response = await fetch("/api/simulate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(collectFormPayload()),
  });

  const payload = await response.json();
  if (!response.ok) {
    elements.formStatus.textContent = payload.error || "Noe gikk galt.";
    return;
  }

  state.simulation = payload;
  state.phaseIndex = 0;
  state.phaseProgress = 0;
  state.playing = true;
  state.lastFrameTime = performance.now();
  elements.playToggle.textContent = "Pause";
  elements.formStatus.textContent = `${payload.method.name} klar. Animasjonen spiller.`;
  updateInfoPanel();
  resizeCanvas();
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const bounds = elements.canvas.getBoundingClientRect();
  elements.canvas.width = Math.round(bounds.width * ratio);
  elements.canvas.height = Math.round(bounds.height * ratio);
  const context = elements.canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function toScreen(point, plot, view) {
  return {
    x: plot.left + ((point.t - view.x_min) / (view.x_max - view.x_min)) * plot.width,
    y: plot.top + plot.height - ((point.y - view.y_min) / (view.y_max - view.y_min)) * plot.height,
  };
}

function drawBackground(context, width, height) {
  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, "#07121b");
  gradient.addColorStop(1, "#122436");
  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);

  const glow = context.createRadialGradient(width * 0.8, height * 0.18, 0, width * 0.8, height * 0.18, width * 0.35);
  glow.addColorStop(0, "rgba(20, 199, 187, 0.12)");
  glow.addColorStop(1, "rgba(20, 199, 187, 0)");
  context.fillStyle = glow;
  context.fillRect(0, 0, width, height);
}

function drawGrid(context, plot, view) {
  context.strokeStyle = "rgba(146, 183, 214, 0.12)";
  context.lineWidth = 1;
  context.font = '12px "Avenir Next", "Segoe UI", sans-serif';
  context.fillStyle = "rgba(214, 231, 245, 0.66)";

  for (let index = 0; index <= 5; index += 1) {
    const ratio = index / 5;
    const x = plot.left + ratio * plot.width;
    const y = plot.top + ratio * plot.height;

    context.beginPath();
    context.moveTo(x, plot.top);
    context.lineTo(x, plot.top + plot.height);
    context.stroke();

    context.beginPath();
    context.moveTo(plot.left, y);
    context.lineTo(plot.left + plot.width, y);
    context.stroke();

    const tickX = lerp(view.x_min, view.x_max, ratio);
    const tickY = lerp(view.y_max, view.y_min, ratio);
    context.fillText(fmt(tickX), x - 12, plot.top + plot.height + 24);
    context.fillText(fmt(tickY), plot.left - 56, y + 4);
  }
}

function drawSlopeField(context, plot, simulation) {
  const backdrop = "#08131d";
  const color = mixColor(simulation.method.color, backdrop, 0.78);
  const xScale = plot.width / (simulation.view.x_max - simulation.view.x_min);
  const yScale = plot.height / (simulation.view.y_max - simulation.view.y_min);
  context.strokeStyle = color;
  context.lineWidth = 1;

  simulation.slope_field.forEach((sample) => {
    const center = toScreen(sample, plot, simulation.view);
    const vx = xScale;
    const vy = -sample.slope * yScale;
    const norm = Math.hypot(vx, vy);
    if (!Number.isFinite(norm) || norm === 0) {
      return;
    }
    const dx = (10 * vx) / norm;
    const dy = (10 * vy) / norm;
    context.beginPath();
    context.moveTo(center.x - dx, center.y - dy);
    context.lineTo(center.x + dx, center.y + dy);
    context.stroke();
  });
}

function drawPolyline(context, points, color, width, dash = []) {
  if (points.length < 2) {
    return;
  }
  context.save();
  context.strokeStyle = color;
  context.lineWidth = width;
  context.setLineDash(dash);
  context.beginPath();
  context.moveTo(points[0].x, points[0].y);
  for (let index = 1; index < points.length; index += 1) {
    context.lineTo(points[index].x, points[index].y);
  }
  context.stroke();
  context.restore();
}

function drawOrb(context, point, color, radius) {
  const outer = context.createRadialGradient(point.x, point.y, 0, point.x, point.y, radius * 4);
  outer.addColorStop(0, `${color}ff`);
  outer.addColorStop(1, `${color}00`);
  context.fillStyle = outer;
  context.beginPath();
  context.arc(point.x, point.y, radius * 4, 0, Math.PI * 2);
  context.fill();

  context.fillStyle = color;
  context.beginPath();
  context.arc(point.x, point.y, radius, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = "rgba(255,255,255,0.9)";
  context.lineWidth = 1.3;
  context.stroke();
}

function drawTangent(context, plot, simulation, point, slope, color, lengthScale = 1, width = 2) {
  const view = simulation.view;
  const deltaT = 0.22 * simulation.problem.h * lengthScale;
  const left = { t: point.t - deltaT, y: point.y - slope * deltaT };
  const right = { t: point.t + deltaT, y: point.y + slope * deltaT };
  const start = toScreen(left, plot, view);
  const end = toScreen(right, plot, view);
  context.save();
  context.strokeStyle = color;
  context.lineWidth = width;
  context.beginPath();
  context.moveTo(start.x, start.y);
  context.lineTo(end.x, end.y);
  context.stroke();
  context.restore();
}

function drawScene() {
  const context = elements.canvas.getContext("2d");
  const width = elements.canvas.clientWidth;
  const height = elements.canvas.clientHeight;
  context.clearRect(0, 0, width, height);
  drawBackground(context, width, height);

  const plot = {
    left: 78,
    top: 54,
    width: width - 110,
    height: height - 96,
  };

  context.fillStyle = "rgba(255,255,255,0.02)";
  context.fillRect(plot.left, plot.top, plot.width, plot.height);

  if (!state.simulation) {
    context.fillStyle = "rgba(228, 238, 245, 0.84)";
    context.font = '600 24px "Iowan Old Style", Georgia, serif';
    context.fillText("Start en simulering for a se animasjonen.", plot.left + 26, plot.top + 48);
    return;
  }

  const simulation = state.simulation;
  drawGrid(context, plot, simulation.view);
  drawSlopeField(context, plot, simulation);

  const referencePoints = simulation.reference.points.map((point) => toScreen(point, plot, simulation.view));
  drawPolyline(context, referencePoints, "rgba(236, 246, 255, 0.84)", 2, [6, 5]);

  const tracePoints = simulation.trace.points.map((point) => toScreen(point, plot, simulation.view));
  drawPolyline(context, tracePoints, mixColor(simulation.method.color, "#09131c", 0.6), 2, [3, 6]);

  const phase = currentPhase();
  const step = currentStep();
  const completed = simulation.trace.points.slice(0, step.index + 1);
  if (phase.kind === "advance") {
    completed.push(lerpPoint(phase.start_point, phase.end_point, state.phaseProgress));
  }
  const activePath = completed.map((point) => toScreen(point, plot, simulation.view));
  drawPolyline(context, activePath, mixColor(simulation.method.color, "#ffffff", 0.28), 10);
  drawPolyline(context, activePath, mixColor(simulation.method.color, "#ffffff", 0.08), 5);
  drawPolyline(context, activePath, simulation.method.color, 2.5);

  tracePoints.forEach((point, index) => {
    context.beginPath();
    context.arc(point.x, point.y, index <= step.index ? 3 : 2, 0, Math.PI * 2);
    context.fillStyle = index <= step.index
      ? mixColor(simulation.method.color, "#09131c", 0.2)
      : "rgba(214, 230, 244, 0.3)";
    context.fill();
  });

  const startScreen = toScreen({ t: step.t, y: step.y }, plot, simulation.view);
  const endScreen = toScreen({ t: step.t_next, y: step.y_next }, plot, simulation.view);
  drawPolyline(
    context,
    [startScreen, endScreen],
    mixColor(simulation.method.color, "#09131c", 0.45),
    2,
    [8, 8]
  );

  step.stage_samples.forEach((stage, index) => {
    const stageScreen = toScreen(stage, plot, simulation.view);
    const isVisible = phase.kind === "advance" || index < phase.stage_index;
    const isActive = phase.kind === "stage" && index === phase.stage_index;
    drawTangent(
      context,
      plot,
      simulation,
      stage,
      stage.slope,
      isActive ? mixColor(simulation.method.color, "#ffffff", 0.2) : mixColor(simulation.method.color, "#09131c", 0.18),
      isActive ? Math.max(state.phaseProgress, 0.18) : 1,
      isActive ? 3 : 1
    );

    context.beginPath();
    context.arc(stageScreen.x, stageScreen.y, 4, 0, Math.PI * 2);
    context.fillStyle = isVisible || isActive
      ? mixColor(simulation.method.color, "#ffffff", 0.18)
      : "rgba(255, 255, 255, 0.05)";
    context.fill();
    context.fillStyle = "rgba(236, 245, 255, 0.9)";
    context.font = '700 12px "Avenir Next", "Segoe UI", sans-serif';
    context.fillText(`k${stage.stage_number}`, stageScreen.x + 10, stageScreen.y - 10);
  });

  let activePoint;
  if (phase.kind === "stage") {
    activePoint = lerpPoint(phase.start_point, phase.end_point, state.phaseProgress);
  } else {
    activePoint = lerpPoint(phase.start_point, phase.end_point, state.phaseProgress);
  }

  drawOrb(context, startScreen, "#ffffff", 5);
  drawOrb(context, toScreen(activePoint, plot, simulation.view), simulation.method.color, 7);

  context.fillStyle = "rgba(244, 249, 255, 0.95)";
  context.font = '600 15px "Avenir Next", "Segoe UI", sans-serif';
  context.fillText(`${simulation.method.name} / ${simulation.problem.function}`, plot.left, 28);
  context.fillStyle = "rgba(188, 208, 226, 0.74)";
  context.font = '12px "Avenir Next", "Segoe UI", sans-serif';
  context.fillText("Lys kule = aktiv beregning. Stiplet linje = det diskrete neste steget.", plot.left, height - 24);
}

function tick(timestamp) {
  if (!state.lastFrameTime) {
    state.lastFrameTime = timestamp;
  }
  const delta = timestamp - state.lastFrameTime;
  state.lastFrameTime = timestamp;

  if (state.simulation && state.playing) {
    const phase = currentPhase();
    const progressIncrement = (delta * state.speed) / phase.duration_ms;
    state.phaseProgress += progressIncrement;

    if (state.phaseProgress >= 1) {
      state.phaseProgress = 0;
      if (state.phaseIndex < state.simulation.phases.length - 1) {
        state.phaseIndex += 1;
      } else {
        state.phaseIndex = 0;
      }
      updateInfoPanel();
    }
  }

  drawScene();
  requestAnimationFrame(tick);
}

function togglePlayback() {
  state.playing = !state.playing;
  elements.playToggle.textContent = state.playing ? "Pause" : "Spill";
}

function restartPlayback() {
  state.phaseIndex = 0;
  state.phaseProgress = 0;
  state.playing = true;
  elements.playToggle.textContent = "Pause";
  updateInfoPanel();
}

function applyPreset(name) {
  const preset = presets[name];
  if (!preset) {
    return;
  }
  elements.functionInput.value = preset.function;
  elements.exactInput.value = preset.exact_function;
  elements.methodSelect.value = preset.method;
  elements.t0Input.value = preset.t0;
  elements.y0Input.value = preset.y0;
  elements.hInput.value = preset.h;
  elements.stepsInput.value = preset.steps;
  elements.refinementInput.value = preset.refinement;
}

async function init() {
  await loadMethods();
  elements.form.addEventListener("submit", simulate);
  elements.playToggle.addEventListener("click", togglePlayback);
  elements.restartButton.addEventListener("click", restartPlayback);
  elements.speedInput.addEventListener("input", () => {
    state.speed = Number(elements.speedInput.value);
    elements.overlaySpeed.textContent = `${state.speed.toFixed(1)}x`;
    updateInfoPanel();
  });
  elements.presetButtons.forEach((button) => {
    button.addEventListener("click", () => {
      applyPreset(button.dataset.preset);
    });
  });
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
  updateInfoPanel();
  await simulate();
  requestAnimationFrame(tick);
}

init().catch((error) => {
  elements.formStatus.textContent = `Kunne ikke starte appen: ${error}`;
});
