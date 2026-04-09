import time
import random

class ActionError(Exception):
    pass

class StateEngine:
    def __init__(self):
        self.state = 'IDLE'
        self.attempts = 0
        self.max_attempts = 3
        self.backoff_factor = 2
        self.base_delay = 1

    def transition(self, new_state):
        if hasattr(self, f'on_enter_{new_state}')):
            getattr(self, f'on_enter_{new_state}')()
        self.state = new_state
        print(f'Transitioned to state: {self.state}')

    def on_enter_OPEN_APP(self):
        # Simulate opening an app with mouse and keyboard actions
        try:
            self.simulate_open_app()
        except Exception as e:
            self.handle_failure(e)

    def simulate_open_app(self):
        # Placeholder for actual GUI automation to open TextEdit
        print('Opening TextEdit...')
        time.sleep(random.uniform(0.5, 1.5))  # Simulate time taken to perform action

    def on_enter_WAIT_MARKER(self):
        # Simulate waiting for a specific marker in the application
        try:
            self.simulate_wait_marker()
        except Exception as e:
            self.handle_failure(e)

    def simulate_wait_marker(self):
        # Placeholder for actual GUI automation to wait for a marker
        print('Waiting for TextEdit to be ready...')
        time.sleep(random.uniform(0.5, 1.5))  # Simulate time taken to perform action

    def on_enter_TYPE(self):
        # Simulate typing text into the application
        try:
            self.simulate_type()
        except Exception as e:
            self.handle_failure(e)

    def simulate_type(self):
        # Placeholder for actual GUI automation to type text
        print('Typing "hello world"...')
        time.sleep(random.uniform(0.5, 1.5))  # Simulate time taken to perform action

    def on_enter_SAVE(self):
        # Simulate saving the file with mouse and keyboard actions
        try:
            self.simulate_save()
        except Exception as e:
            self.handle_failure(e)

    def simulate_save(self):
        # Placeholder for actual GUI automation to save a file
        print('Saving file...')
        time.sleep(random.uniform(0.5, 1.5))  # Simulate time taken to perform action

    def on_enter_DONE(self):
        print('Task completed successfully.')

    def handle_failure(self, exception):
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            raise ActionError(f'Failed after {self.max_attempts} attempts: {exception}')
        delay = self.base_delay * (self.backoff_factor ** (self.attempts - 1))
        print(f'Retrying in {delay:.2f} seconds...')
        time.sleep(delay)

    def run(self):
        while self.state != 'DONE':
            if self.state == 'IDLE':
                self.transition('OPEN_APP')
            elif self.state == 'OPEN_APP':
                self.transition('WAIT_MARKER')
            elif self.state == 'WAIT_MARKER':
                self.transition('TYPE')
            elif self.state == 'TYPE':
                self.transition('SAVE')
            elif self.state == 'SAVE':
                self.transition('DONE')

if __name__ == '__main__':
    engine = StateEngine()
    try:
        engine.run()
    except ActionError as e:
        print(e)
