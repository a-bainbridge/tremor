import time


class Stopwatch:  # counts seconds
    def __init__(self, start=False):
        self.running = False
        self.begin = 0
        self.current = 0
        self.passed = 0
        if start:
            self.start()

    def start(self):
        if self.running:
            print('stopwatch already started!')
        self.running = True
        self.begin = time.perf_counter()

    def update(self):
        self.current = time.perf_counter()
        self.passed = self.current - self.begin

    def check(self) -> float:
        self.update()
        return self.passed


class FPSController(Stopwatch):
    def __init__(self, start=False):
        Stopwatch.__init__(self, start)
        self.average_fps = 0
        self.frames = 0

    def add_frame(self):
        self.frames += 1

    def update(self):
        Stopwatch.update(self)
        self.average_fps = self.frames / self.passed

    def capFPS(self, fps: float = 60):
        self.add_frame()
        self.update()
        while self.average_fps > fps:
            self.update()
