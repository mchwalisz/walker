# import numpy as np

import networkx as nx
import pandas as pd

from bokeh.models import BoxSelectTool
from bokeh.models import Circle
from bokeh.models import HoverTool
from bokeh.models import MultiLine
from bokeh.models import TapTool
from bokeh.models.graphs import EdgesAndLinkedNodes
from bokeh.models.graphs import NodesAndLinkedEdges
from bokeh.models.graphs import from_networkx
from bokeh.palettes import Spectral4
from bokeh.plotting import figure
from pathlib import Path

CURR_PATH = Path(__file__).parent

background = {
    "name": "twistmap/tub-hft-3.og.png",
    "origin_x": -6.59,
    "origin_y": -2.97,
    "x": 3862,
    "y": 2243,
    "resolution": 0.01,
}

nodes = pd.read_csv(CURR_PATH / "wifi_nodes.csv")
nodes["floor"] = nodes["room"].str[2].astype(int)
nodes = nodes[(nodes["floor"] == 3) & (nodes["status"] == "on")]
nodes = nodes[nodes["platform"] == "nuc"]

node_positions = nodes.set_index("node_id")[["x", "y"]].to_dict("index")
for key in node_positions:
    pos = node_positions[key]
    node_positions[key] = (pos["x"], pos["y"])


def create_map():
    p = figure(
        x_range=(-1, 32),
        y_range=(-1, 16),
        plot_width=320,
        plot_height=160,
        toolbar_location="above",
        title="TWIST 3rd floor",
        sizing_mode="scale_width",
        # output_backend="webgl",
    )
    p.xaxis.axis_label = "X [m]"
    p.yaxis.axis_label = "Y [m]"

    p.image_url(
        url=[background["name"]],
        x=background["origin_x"],
        y=background["origin_y"],
        w=background["x"] * background["resolution"],
        h=background["y"] * background["resolution"],
        anchor="bottom_left",
    )
    return p


def draw_graph(plot, G):
    plot.add_tools(HoverTool(tooltips=None), TapTool(), BoxSelectTool())
    graph = from_networkx(
        G, nx.spring_layout, pos=node_positions, fixed=node_positions.keys()
    )

    graph.node_renderer.glyph = Circle(size=15, fill_color=Spectral4[0])
    graph.node_renderer.selection_glyph = Circle(size=15, fill_color=Spectral4[2])
    graph.node_renderer.hover_glyph = Circle(size=15, fill_color=Spectral4[1])

    graph.edge_renderer.glyph = MultiLine(
        line_color="#CCCCCC", line_alpha=0.8, line_width=5
    )
    graph.edge_renderer.selection_glyph = MultiLine(
        line_color=Spectral4[2], line_width=5
    )
    graph.edge_renderer.hover_glyph = MultiLine(line_color=Spectral4[1], line_width=5)

    graph.selection_policy = NodesAndLinkedEdges()
    graph.inspection_policy = EdgesAndLinkedNodes()

    plot.renderers.append(graph)
    return plot
