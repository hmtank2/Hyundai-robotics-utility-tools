import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from graph_motion import GraphPoint, advance
from job_signal_viewer import Explorer, GraphNeighbor


class GraphMotionTests(unittest.TestCase):
    def test_hover_grows_and_returns_to_normal(self):
        points = [GraphPoint(0, 0, 0, 0)]
        self.assertTrue(advance(points, 0, None, (0, 0)))
        self.assertGreater(points[0].scale, 1)
        for _ in range(50):
            advance(points, None, None, None)
        self.assertAlmostEqual(points[0].scale, 1, places=5)

    def test_neighbor_moves_away_from_hovered_node(self):
        points = [GraphPoint(0, 0, 0, 0), GraphPoint(30, 0, 30, 0)]
        advance(points, 0, None, (0, 0))
        self.assertGreater(points[1].x, 30)

    def test_dragged_node_stays_under_pointer(self):
        point = GraphPoint(80, 40, 0, 0, vx=2)
        advance([point], None, 0, (80, 40))
        self.assertEqual((point.x, point.y, point.vx), (80, 40, 0))

    def test_click_navigates_but_drag_reanchors(self):
        visited = []
        point = GraphPoint(80, 40, 40, 40)
        graph = SimpleNamespace(
            graph_drag=0, graph_press=(80, 40), graph_moved=False,
            graph_nodes=[GraphNeighbor(('file', '9250.job'), 'out')],
            graph_points=[point], graph_hover=0, graph_pointer=(80, 40),
            show_node=visited.append, start_graph_animation=lambda: None,
        )
        Explorer.graph_release_node(graph, None)
        self.assertEqual(visited, [('file', '9250.job')])

        graph.graph_drag, graph.graph_moved = 0, True
        Explorer.graph_release_node(graph, None)
        self.assertEqual((point.anchor_x, point.anchor_y), (80, 40))
        self.assertEqual(len(visited), 1)


if __name__ == '__main__':
    unittest.main()
