from enum import Enum
import time
from threading import Event, Thread


class EventType(Enum):
    STATE_CHANGED = "StateChanged"
    ACTION_FAILED = "ActionFailed"


class GUIController:
    def __init__(self):
        self.listeners = {}
        self.current_state = None
        self.event_queue = []
        self._running = Event()
        self.thread = Thread(target=self.process_events)
        self.thread.start()

    def subscribe(self, event_type: EventType, callback):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback):
        if event_type in self.listeners and callback in self.listeners[event_type]:
            self.listeners[event_type].remove(callback)

    def publish_event(self, event_type: EventType, data=None):
        self.event_queue.append((event_type, data))

    def process_events(self):
        while not self._running.is_set():
            if self.event_queue:
                event_type, data = self.event_queue.pop(0)
                for callback in self.listeners.get(event_type, []):
                    try:
                        callback(data)
                    except Exception as e:
                        print(f"Callback error: {e}")
            time.sleep(0.1)

    def stop(self):
        self._running.set()
        self.thread.join()

