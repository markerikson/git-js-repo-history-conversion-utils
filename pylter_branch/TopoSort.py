# -*- coding: utf-8 -*-

from collections import defaultdict


class TopoSort:
    def __init__(self):
        self.vertices = set()
        self.edges = defaultdict(set)

    def add_edge(self, source, destination):
        self.add_vertex(source)
        self.add_vertex(destination)
        self.edges[source].add(destination)

    def add_vertex(self, vertex):
        self.vertices.add(vertex)

    def sort(self):
        ingrees = { v : 0 for v in self.vertices }
        for neighbours in self.edges.values():
            for u in neighbours:
                ingrees[u] += 1

        non_processed = self.vertices.copy()
        queue = [ v for v, ingree in ingrees.items() if ingree == 0 ]
        topo_order = []

        while queue:
            u = queue.pop(0)
            topo_order.append(u)
            neighbours = self.edges[u]
            for v in neighbours:
                ingrees[v] -= 1
                if ingrees[v] == 0:
                    queue.append(v)
            non_processed.remove(u)

        if len(non_processed):
            raise RuntimeError("Cycles are in graph")

        return topo_order
