"""The opening bar: each phase of `Desktop.open` owns a share of 0..1 by its typical time; measured work moves
inside the share, and a phase without a measurable loop creeps toward (never past) its end. Never moves back."""
import math
import threading
import time

# typical seconds on a mid-size archive (mapsaud); the share each phase owns follows from them
WEIGHTS = {"Unpacking archive": 1.0, "Building archive data": 1.7, "Building pages": 5.5, "Starting reader": 1.2}
LOOP = {"Building archive data": 0.12, "Building pages": 0.35}      # the part of a phase its measured loop covers
CHECKING = 0.03                                       # the share of the first look at the folder
TAU = {k: v / 2.5 for k, v in WEIGHTS.items()}                       # creep: ~92% of a phase at its typical time


class Meter:
    def __init__(self, report, stages=()):
        self.report = report
        self.lock = threading.Lock()
        self.fraction = 0.0
        self.stage = "Checking archive"
        self.start, self.end = 0.0, CHECKING
        self.began = time.monotonic()
        self.stop = threading.Event()
        self.shares = {}
        self.plan(stages)
        self._push()
        self.thread = threading.Thread(target=self._tick, name="hydra-progress", daemon=True)
        self.thread.start()

    def plan(self, stages):
        """Divide what is left after the first look between the phases that will run."""
        with self.lock:
            total = sum(WEIGHTS[s] for s in stages) or 1.0
            at, self.shares = max(CHECKING, self.fraction), {}
            room = 1 - at
            for s in stages:
                self.shares[s] = (at, at + room * WEIGHTS[s] / total * 0.99)
                at = self.shares[s][1]

    def phase(self, stage):
        with self.lock:
            self.stage = stage
            self.start, self.end = self.shares.get(stage, (self.fraction, self.fraction))
            self.start = max(self.start, self.fraction)
            self.end = max(self.end, self.start)
            self.began = time.monotonic()
        self._push()

    def measured(self, done, total):
        """Real work inside the current phase: done of total."""
        if not total:
            return
        with self.lock:
            self._raise(self.start + (self.end - self.start) * LOOP.get(self.stage, 0.5) * min(done / total, 1.0))
        self._push()

    def _raise(self, value):
        self.fraction = max(self.fraction, min(value, self.end))

    def _tick(self):
        while not self.stop.wait(0.1):
            with self.lock:
                spent = time.monotonic() - self.began
                tau = TAU.get(self.stage, 1.0)
                self._raise(self.start + (self.end - self.start) * 0.95 * (1 - math.exp(-spent / tau)))
            self._push()

    def _push(self):
        with self.lock:
            stage, fraction = self.stage, self.fraction
        self.report(stage, fraction)

    def done(self):
        self.stop.set()
        self.thread.join()
