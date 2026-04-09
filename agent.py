"""agent.py — The Orchestrator: main loop, history management, guardrails."""

import time
import sys
from dotenv import load_dotenv

import screen
import brain
import executor

load_dotenv()

MAX_STEPS = 20
MAX_SECONDS = 300  # 5 minutes
STUCK_REPEAT_LIMIT = 3

# --- P2: Dynamic delays per action type ---
_ACTION_DELAYS = {
    "shell": 2.5,         # app launches need time
    "press": 0.8,         # navigation / hotkeys
    "click": 0.4,
    "click_marker": 0.4,
    "type": 0.15,
    "scroll": 0.2,
    "done": 0.0,
}
_NAV_KEYS = {"enter", "return", "cmd+l", "cmd+t", "cmd+w", "cmd+r"}


def _get_step_delay(action: dict) -> float:
    act = action.get("action", "")
    if act == "press":
        key = (action.get("text") or "").lower()
        if key in _NAV_KEYS:
            return 1.5   # navigation triggers page loads
    return _ACTION_DELAYS.get(act, 1.0)


def _action_signature(action: dict) -> str:
    """Compact string to detect repeated actions."""
    return f"{action.get('action')}:{action.get('coordinates')}:{action.get('text')}"


def run_task(task: str, max_steps: int = MAX_STEPS):
    """Run the agent loop for the given task."""
    print(f"\n{'='*60}")
    print(f"TASK: {task}")
    print(f"{'='*60}\n")

    history: list[dict] = []
    start_time = time.time()
    recent_signatures: list[str] = []

    # P3: screen change detection
    prev_hash: str | None = None
    no_change_count = 0

    # P4: element map (populated each step after markers.py is integrated)
    element_map: dict = {}

    for step in range(1, max_steps + 1):
        elapsed = time.time() - start_time
        if elapsed > MAX_SECONDS:
            print(f"\n[ABORT] Time limit ({MAX_SECONDS}s) exceeded.")
            break

        print(f"[Step {step}] Capturing screen...")
        img = screen.capture_screen()
        img_b64, scale_x, scale_y = screen.image_to_base64(img)
        img_w = round(img.width / scale_x)
        img_h = round(img.height / scale_y)

        # P3: check if screen changed since last step
        curr_hash = screen.image_hash(img)
        if prev_hash is not None and curr_hash == prev_hash:
            no_change_count += 1
            if no_change_count >= 2 and history:
                history[-1]["hint"] = "Previous action did not change the screen — try a completely different approach."
                print(f"[Step {step}] Screen unchanged ({no_change_count}x) — injecting hint.")
        else:
            no_change_count = 0
        prev_hash = curr_hash

        # P4 hook: markers integration (imported conditionally to avoid breaking
        # if markers.py is not yet present)
        try:
            import markers as _markers
            element_map, ax_ok = _markers.get_interactive_elements(
                scale_x, scale_y, img.width, img.height)
            if ax_ok and element_map:
                # Compute resized PIL image for annotation
                resized_w = img_w
                resized_h = img_h
                resized_img = img.resize((resized_w, resized_h))
                annotated = _markers.annotate_screenshot(resized_img, element_map)
                img_b64 = screen.encode_pil(annotated)
                print(f"[Step {step}] Markers: {len(element_map)} elements annotated.")
            else:
                element_map = {}
        except ImportError:
            element_map = {}
        except Exception as _ex:
            print(f"[Step {step}] Markers error: {_ex}")
            element_map = {}

        markers_available = bool(element_map)

        print(f"[Step {step}] Reasoning with Claude... (image {img_w}x{img_h}, scale {scale_x:.2f}x)")
        try:
            action = brain.decide_action(
                img_b64, task, history,
                img_w=img_w, img_h=img_h,
                markers_available=markers_available,
                n_markers=len(element_map),
            )
        except Exception as e:
            print(f"[Step {step}] Brain error: {e}")
            break

        thought = action.get("thought", "")
        act = action.get("action", "?")
        coords = action.get("coordinates")
        text = action.get("text")
        status = action.get("status", "continue")

        # Format display
        if act == "click_marker":
            act_display = f'click_marker(#{text})'
        elif coords:
            act_display = f"{act}({coords[0]}, {coords[1]})"
        elif text:
            act_display = f'{act}("{text}")'
        else:
            act_display = act

        print(f"[Step {step}] THINK: {thought}")
        print(f"[Step {step}] ACTION: {act_display}")

        if act == "done" or status == "done":
            print(f"\n[DONE] Task completed in {step} step(s).")
            break

        if status == "stuck":
            print(f"\n[STUCK] Agent reported it is stuck. Aborting.")
            break

        # Stuck detection: repeated identical actions
        sig = _action_signature(action)
        recent_signatures.append(sig)
        if len(recent_signatures) > STUCK_REPEAT_LIMIT:
            recent_signatures.pop(0)
        if len(recent_signatures) == STUCK_REPEAT_LIMIT and len(set(recent_signatures)) == 1:
            print(f"\n[ABORT] Detected {STUCK_REPEAT_LIMIT} identical consecutive actions. Aborting.")
            break

        # Execute
        success, shell_output = executor.execute(action, scale_x=scale_x, scale_y=scale_y,
                                                 element_map=element_map)
        if not success:
            print(f"[Step {step}] Execution failed, continuing...")

        # Record history (text only)
        entry = {"action": act, "coordinates": coords, "text": text, "thought": thought}
        if shell_output:
            entry["shell_output"] = shell_output
        history.append(entry)

        # P2: dynamic delay
        delay = _get_step_delay(action)
        print(f"[Step {step}] Waiting {delay:.1f}s...\n")
        time.sleep(delay)

    else:
        print(f"\n[ABORT] Max steps ({max_steps}) reached without completing task.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"<task description>\"")
        print('\nExample: python agent.py "Open TextEdit and type Hello World"')
        sys.exit(1)

    task_description = " ".join(sys.argv[1:])
    run_task(task_description)
