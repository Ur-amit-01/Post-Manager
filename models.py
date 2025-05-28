class ForwarderState:
    def __init__(self):
        self._forwarding = False

    @property
    def is_forwarding(self) -> bool:
        return self._forwarding

    def start_forwarding(self):
        self._forwarding = True

    def stop_forwarding(self):
        self._forwarding = False
