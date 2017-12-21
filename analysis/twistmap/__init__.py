# import numpy as np

import pandas as pd
from pathlib import Path

from bokeh.layouts import column
from bokeh.models import ColumnDataSource
from bokeh.models import HoverTool
from bokeh.models import LabelSet
from bokeh.palettes import Colorblind8
from bokeh.plotting import curdoc
from bokeh.plotting import figure
from bokeh.transform import factor_cmap

CURR_PATH = Path(__file__).parent()

backgrounds = {
    'name': CURR_PATH / 'tub-hft-2.og.png',
    'origin_x': -7.95,
    'origin_y': -2.97,
    'x': 3998,
    'y': 2243,
    'resolution': 0.01,
}

nodes = pd.read_csv(CURR_PATH / 'wifi_nodes.csv')
nodes['floor'] = nodes['room'].str[2].astype(int)

pmap = factor_cmap(
    'platform',
    palette=Colorblind8,
    factors=sorted(nodes.platform.unique()))


def plot_floor(floor=2):
    p = figure(
        x_range=(-1, 32), y_range=(-1, 16),
        plot_width=320, plot_height=160,
        tools='hover,save,pan,box_zoom,reset,wheel_zoom',
        toolbar_location='above',
        title='TWIST TKN floor {}'.format(floor),
        # output_backend="webgl",
    )
    p.xaxis.axis_label = 'X [m]'
    p.yaxis.axis_label = 'Y [m]'

    p.select_one(HoverTool).tooltips = [
        ("node", "@node_id"),
        ("platform", "@platform"),
        ("position", "@x, @y, @z"),
    ]
    p.image_url(
        url=[backgrounds[floor]['name']],
        x=backgrounds[floor]['origin_x'],
        y=backgrounds[floor]['origin_y'],
        w=backgrounds[floor]['x'] * backgrounds[floor]['resolution'],
        h=backgrounds[floor]['y'] * backgrounds[floor]['resolution'],
        anchor='bottom_left',
    )

    floor_nodes = nodes[(nodes['floor'] == floor) & (nodes['status'] == 'on')]
    for platform, color in zip(nodes.platform.unique(), Colorblind8):
        source = ColumnDataSource(
            floor_nodes[floor_nodes['platform'] == platform])
        p.scatter(
            source=source,
            x='x', y='y',
            color=color,
            size=10,
            legend=platform,
        )
        # labels = LabelSet(
        #     x='x', y='y', angle=0.6,
        #     text_font_size="9px",
        #     text='node_id', level='glyph',
        #     x_offset=3, y_offset=5, source=source, render_mode='canvas',
        # )
        # p.add_layout(labels)

    p.legend.location = "top_right"
    p.legend.click_policy = 'hide'

    return p


plots = column([plot_floor(x) for x in range(2, 5)], sizing_mode='scale_width')
# show(p)  # open a browser
curdoc().add_root(plots)
curdoc().title = "TWIST map"
curdoc()
