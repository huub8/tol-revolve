
class Timers:
    def __init__(self, names, current_time):
        self.timers = {name: current_time for name in names}

    def is_it_time(self, name, time_period, current_time):
        last_time = self.timers[name]

        if last_time is not None:
            elapsed = current_time - last_time
            if elapsed >= time_period:
                return True

        return False


    def reset(self, name, current_time):
        self.timers[name] = current_time