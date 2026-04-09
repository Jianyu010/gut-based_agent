# GUI Agent (macOS) — Revised Architecture Plan

> **Status**: Fresh rewrite. Previous prototype abandoned due to (1) 10–30s per action latency from overusing heavy VLM, (2) coordinate mismatch causing consistently wrong clicks.

---

## Root Cause Analysis

| Problem | Root Cause | Fix |
|---|---|---|
| VLM says "click (234, 456)" but misses target | Coordinate system mismatch (retina scaling, window offsets, screen size variation) | Never use raw VLM coordinates for clicking |
| 10–30s per action | Heavy VLM called for every frame + every decision | Tiered pipeline; heavy VLM only for planning, not clicking |
| Wrong shortcut keys | VLM guessing app-specific shortcuts | Software-defined shortcut registry per app |
| Click drift on different screen sizes | No coordinate normalization strategy | Accessibility API returns native logical coords regardless of resolution |

---

## Core Design Principle

> **Separate what software can solve from what AI must solve.**
>
> Software is fast, deterministic, and pixel-perfect.  
> VLM/LLM is slow, probabilistic, and expensive.  
> Use each only where it has an advantage.

---

## Architecture: Five Layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 5: Goal / Task Manager                           │
│  Heavy LLM — Claude Opus 4.6 (API)                      │
│  Called: once per user goal, and on recovery            │
│  Input:  user goal (natural language)                   │
│  Output: ordered sub-task list (no coordinates)         │
└────────────────────────┬────────────────────────────────┘
                         │ sub-tasks
┌────────────────────────▼────────────────────────────────┐
│  LAYER 4: State Reasoner                                │
│  Small offline VLM — moondream2 or Qwen2.5-VL 3B        │
│  Called: on each screen change                          │
│  Input:  current screenshot + current sub-task          │
│  Output: semantic state label + intent + confidence     │
│  Rule:   if confidence < threshold → escalate to T2/T3  │
└────────────────────────┬────────────────────────────────┘
                         │ intent (e.g., "click Save button")
┌────────────────────────▼────────────────────────────────┐
│  LAYER 3: Element Resolver  ← SOLVES COORDINATE PROBLEM │
│  macOS Accessibility API (AXUIElement via atomacos)     │
│  Called: for every action that targets a UI element     │
│  Input:  intent / element description                   │
│  Output: exact native bounding box (retina-aware)       │
│  Fallback: CV template matching within a VLM-hinted ROI │
│  NOTE: VLM never provides final (x, y) coordinates      │
└────────────────────────┬────────────────────────────────┘
                         │ element rect
┌────────────────────────▼────────────────────────────────┐
│  LAYER 2: Action Planner (fully software-defined)       │
│  App shortcut registry, scroll strategies, drag rules   │
│  Input:  element rect + action type                     │
│  Output: parameterized, sequenced action list           │
│  e.g.:   smooth bezier mouse path → click center        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  LAYER 1: Executor + Verifier                           │
│  pynput / pyautogui for input simulation                │
│  After each action: diff screenshot to verify change    │
│  Retry with spatial jitter if no screen change detected │
└─────────────────────────────────────────────────────────┘
```

---

## Tiered VLM / LLM Strategy

| Tier | Model | Where it runs | Latency | Role |
|---|---|---|---|---|
| T0 | Pixel diff (no ML) | CPU, always | <5ms | Skip frames with no change |
| T1 | moondream2 or Qwen2.5-VL 3B | Local (ollama) | 200–800ms | State classification, intent extraction, confidence scoring |
| T2 | claude-sonnet-4-6 (API) | Remote | 1–3s | Ambiguous screen description, element disambiguation |
| T3 | claude-opus-4-6 (API) | Remote | 5–10s | Goal decomposition, multi-step planning, error recovery |

**Key rule**: T3 produces a *plan* (steps in natural language), never pixel coordinates. It is never in the per-frame click loop.

---

## The Coordinate Fix (Layer 3 deep-dive)

### Primary path — macOS Accessibility API

- Python library: `atomacos` (wraps `AXUIElement` / `NSAccessibility`)
- Returns each UI element with: role, title, value, enabled state, and **logical bounding box**
- Logical coordinates are retina-aware and window-relative — no manual scaling needed
- Works for: all native macOS apps, most Electron apps, most browsers
- Latency: 1–5ms per lookup

```python
# Conceptual example
import atomacos
app = atomacos.getAppRefByBundleId("com.apple.Safari")
window = app.windows()[0]
save_button = window.findFirst(AXRole="AXButton", AXTitle="Save")
rect = save_button.AXFrame   # exact position, no VLM needed
```

### Fallback path — ROI-scoped template matching

1. Small VLM describes approximate screen region: "blue Save button in top-right of toolbar"
2. Software crops that region (ROI)
3. SIFT / template match runs only on the ROI
4. Returns sub-pixel-accurate center within the region

**VLM provides context. Software provides coordinates. Always.**

---

## Software-Defined Behavior Registry

These must never go through VLM:

```python
APP_SHORTCUTS = {
    "com.apple.finder":   {"new_folder": "cmd+shift+n", "go_home": "cmd+shift+h"},
    "com.apple.Safari":   {"new_tab": "cmd+t", "address_bar": "cmd+l", "refresh": "cmd+r"},
    "com.apple.Terminal": {"new_window": "cmd+n", "clear": "cmd+k"},
    "com.microsoft.VSCode": {"command_palette": "cmd+shift+p", "save": "cmd+s"},
}

SCROLL_STRATEGIES = {
    "AXScrollArea":  "smooth_scroll_with_momentum",
    "AXWebArea":     "page_down_key",
    "AXList":        "arrow_keys",
}

# State transitions that are always software-handled
DETERMINISTIC_TRANSITIONS = {
    "alert_dialog_appeared":  "press_default_button_via_accessibility",
    "file_save_dialog":       "use_shortcut_then_type_path",
    "dropdown_opened":        "arrow_key_navigation",
}
```

---

## Feedback Loop / Retry Logic

```
Execute action
      │
      ▼ wait 200ms
Diff screenshot
      │
      ├─ Screen changed as expected? ──► YES → advance to next sub-task
      │
      ▼ NO
Re-query T1 small VLM with new screenshot
      │
      ├─ T1 identifies new state → retry with corrected element lookup
      │
      ▼ Still stuck after 2 cycles?
Escalate to T3 (Opus) for recovery plan
      │
      ▼ T3 returns revised sub-task list → resume from Layer 4
```

---

## Module Structure

```
gui_agent/
├── capture/
│   ├── screen.py          # mss-based capture, PIL Image output
│   └── diff.py            # pixel diff detector, ROI extractor
│
├── perception/
│   ├── t1_local.py        # moondream2/Qwen wrapper (ollama), returns state + confidence
│   ├── t2_remote.py       # claude-sonnet-4-6 for disambiguation
│   └── state.py           # state label schema, confidence threshold logic
│
├── accessibility/
│   ├── ax_resolver.py     # atomacos wrapper, element lookup by role/title/value
│   └── ax_cache.py        # per-app element tree cache (invalidated on screen change)
│
├── planner/
│   ├── t3_planner.py      # claude-opus-4-6 goal decomposition
│   └── task_queue.py      # sub-task queue, retry state machine
│
├── executor/
│   ├── mouse.py           # bezier-curve smooth movement, click, drag
│   ├── keyboard.py        # type, press, shortcut dispatch
│   └── verifier.py        # post-action diff check, retry-with-jitter
│
├── registry/
│   ├── shortcuts.py       # app shortcut map (bundle ID → action → keys)
│   └── scroll.py          # scroll strategy map (AX role → strategy)
│
└── agent.py               # orchestration loop, escalation logic, guardrails
```

---

## Decision Flow (per frame)

```
Screen change detected (T0 diff)
        │
        ▼
T1 local VLM: classify state, extract intent
        │
        ├─ High confidence ──► Layer 3 (Accessibility lookup) ──► Layer 2 ──► Layer 1
        │
        ▼ Low confidence
T2 remote VLM (Sonnet): describe ambiguous elements
        │
        ├─ Intent now clear ──► Layer 3 ──► Layer 2 ──► Layer 1
        │
        ▼ Task context broken
T3 remote LLM (Opus): re-plan remaining sub-tasks
        │
        └──► restart sub-task queue from Layer 4
```

---

## Dependencies

```
# Core
mss>=9.0.0               # fast screen capture
Pillow>=10.0.0           # image processing
pynput>=1.7.0            # mouse/keyboard simulation
pyautogui>=0.9.54        # fallback input + failsafe

# Accessibility
atomacos>=0.1.0          # macOS AXUIElement Python bindings
pyobjc-framework-ApplicationServices  # lower-level if needed

# Local VLM
ollama>=0.1.0            # local model runtime (moondream2, Qwen2.5-VL)

# Remote LLM
anthropic>=0.40.0        # Claude Sonnet (T2) + Opus (T3)
python-dotenv>=1.0.0

# CV fallback
opencv-python>=4.9.0     # template matching for accessibility fallback
numpy>=1.26.0
```

---

## Development Phases

### Phase 1: Foundation
- [ ] `capture/screen.py` + `capture/diff.py` — screen capture + diff detector
- [ ] `accessibility/ax_resolver.py` — AXUIElement wrapper with element lookup
- [ ] `executor/mouse.py` + `executor/keyboard.py` — input simulation
- [ ] `executor/verifier.py` — post-action diff check
- [ ] Manual test: find "Save" button in TextEdit via accessibility API and click it

### Phase 2: Local Perception
- [ ] `registry/shortcuts.py` — shortcut map for Finder, Safari, Terminal, VSCode
- [ ] `perception/t1_local.py` — moondream2 via ollama, state label + confidence
- [ ] `capture/diff.py` — ROI extraction for fallback CV path
- [ ] `planner/task_queue.py` — sub-task queue + retry state machine
- [ ] Test: "Open Safari and go to google.com" — using only T1 + Accessibility

### Phase 3: Remote LLM Integration
- [ ] `planner/t3_planner.py` — Opus 4.6 goal decomposition
- [ ] `perception/t2_remote.py` — Sonnet disambiguation
- [ ] `agent.py` — full orchestration loop with escalation logic
- [ ] Escalation thresholds tuned by testing
- [ ] Test: multi-step task "Open Notes, create a new note titled 'Test', type 3 lines"

### Phase 4: Robustness
- [ ] `accessibility/ax_cache.py` — element tree caching per app
- [ ] Full retry + jitter logic in verifier
- [ ] Logging: save screenshots, state labels, and actions per run
- [ ] Benchmark: measure T1 vs T3 call ratio (target: >90% actions handled by T1 + software)

---

## Open Questions

1. **Local VLM runtime**: enough VRAM for moondream2 (~2GB) at useful speed, or CPU fallback?
2. **Priority apps**: which apps to test against first to build shortcut registry?
3. **Confidence threshold**: what T1 confidence score triggers T2 escalation? (start: 0.7)
