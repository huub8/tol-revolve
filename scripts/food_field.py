import math


class Grid:

    def __init__(self, xmin, ymin, xmax, ymax, xresol, yresol, value):
        self.x_min = xmin
        self.y_min = ymin
        self.x_max = xmax,
        self.y_max = ymax
        self.x_span = xmax - xmin
        self.y_span = ymax - ymin
        self.cell_size_x = x_span / xresol
        self.cell_size_y = y_span / yresol
        self.x_resol = xresol
        self.y_resol = yresol

        self.values = [[value for _ in range(xresol)] for _ in range(yresol)]


    def find_cell(self, x, y):
        x = x - self.x_min
        y = y - self.y_min
        i = self.x_resol * x / self.x_span
        j = self.y_resol * y / self.y_span

        i = int(math.floor(i))
        j = int(math.floor(j))

        return i, j


    def validate_indices(self, i, j):
        if i < 0:
            i = 0
        elif i >= self.x_resol:
            i = self.x_resol - 1

        if j < 0:
            j = 0
        elif j >= self.y_resol:
            j = self.y_resol - 1

        return i, j


    def get_value(self, x, y):
        i, j = self.find_cell(x, y)
        return self.values[i][j]


    def get_value_safe(self, x, y):
        i, j = self.find_cell(x, y)
        i, j = self.validate_indices(i, j)
        return self.values[i][j]


    def change_value(self, x, y, value_add):
        i, j = self.find_cell(x, y)
        self.values[i][j] = self.values[i][j] + value_add


    def change_value_safe(self, x, y, value_add):
        i, j = self.find_cell(x, y)
        i, j = self.validate_indices(i, j)
        self.values[i][j] = self.values[i][j] + value_add


    def set_value(self, x, y, new_value):
        i, j = self.find_cell(x, y)
        self.values[i][j] = new_value


    def set_value_safe(self, x, y, new_value):
        i, j = self.find_cell(x, y)
        i, j = self.validate_indices(i, j)
        self.values[i][j] = new_value