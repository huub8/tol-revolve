import random
import math
from scipy.spatial import cKDTree

num_points = 10000

points = [(random.uniform(-10.0, 10.0), random.uniform(-10.0, 10.0)) for _ in range(num_points)]


range = 0.02


def dist(point1, point2):
    return math.sqrt( pow(point1[0] - point2[0], 2) + pow(point1[1] - point2[1], 2) )


# compare all to all:

def all_to_all():
    for index, point in enumerate(points):
        for other in points:
            d = dist(point, other)
            if d > 0 and d <= range:
                print "%d: point [%f, %f] is close to [%f, %f] (distance = %f)" % \
                      (index, point[0], point[1], other[0], other[1], d)



def using_tree():
    point_tree = cKDTree(points, leafsize=100)
    for index, point in enumerate(points):
        neighbor=point_tree.query(point, k=2, distance_upper_bound=range)
        print index, ", neighbor = ", neighbor


#all_to_all()
using_tree()