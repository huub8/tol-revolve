
class Timers:
    """
    This class is useful when you want to do some action every T seconds.

    You create Timers object by passing a list of unique names and current time.

    You call the method is_it_time(name, time_period, current_time) to ask whether 'time_period' seconds
    has passed since the moment you created or reset the 'name' timer.

    You set 'name' timer to current time by calling reset(name, current_time).

    You can also add a new 'name' timer by calling reset with the new 'name'.

    """

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


    def get_last_time(self, name):
        return self.timers[name]

