# -*- coding: utf-8 -*-
"""Functions to creating interactive plots from Wikipedia data.
"""

import bokeh.palettes
from bokeh.models import OpenURL, TapTool
import bokeh.plotting
from bokeh.plotting import figure, output_notebook, ColumnDataSource

import pandas as pd
import numpy as np

output_notebook()

__version__ = 2


def show(plot):
    """Show a plot in an Jupyter notebook
    """
    bokeh.plotting.show(plot)


def create_figure(dframe, xvar, yvar, **kwargs):
    """Creates an interactive plot from a pandas data frame.

    Args:
        dframe: A pandas data frame.
        xvar: Name of the x-variable.
        yvar: Name of the y-variable.
        **kwargs: Option keyword arguments that control the plot, including:
            color: Optional name of the color variable.
            url: Optional name of the url variable.
            title: String giving the title of the plot.
            x_axis_label: String to label to the x-axis with.
            y_axis_label: String to label to the y-axis with.
            nsizes: Maximum number of colors to include in continuous plot.

    Returns:
        A bokeh plot object.
    """
    cnames = list(set(dframe.columns) - set([xvar, yvar, kwargs['url']]))
    tooltips = [(x, "@{0:s}".format(x)) for x in cnames]

    if 'x_axis_label' not in kwargs:
        kwargs['x_axis_label'] = xvar
    if 'y_axis_label' not in kwargs:
        kwargs['y_axis_label'] = yvar

    plot = figure(plot_width=950,
                  plot_height=600,
                  tooltips=tooltips,
                  tools="hover,pan,wheel_zoom,reset,tap",
                  toolbar_location="below",
                  toolbar_sticky=True,
                  active_scroll='wheel_zoom',
                  title=kwargs['title'],
                  x_axis_label=kwargs['x_axis_label'],
                  y_axis_label=kwargs['y_axis_label'])

    cval = "#31AADE"
    if kwargs['color'] is not None:
        num_col = np.issubdtype(dframe[kwargs['color']].dtype, np.number)
        if num_col and len(set(dframe[kwargs['color']])) > kwargs['nsizes']:
            codes = pd.qcut(dframe[kwargs['color']].values, kwargs['nsizes'],
                            duplicates='drop').codes
        else:
            codes = pd.Categorical(dframe[kwargs['color']]).codes
        pal = getattr(bokeh.palettes, 'viridis')(np.max(codes) + 1)
        cval = [pal[xx] for xx in codes]

    dframe = dframe.copy(deep=True)
    dframe['COLOR'] = pd.Series(cval, index=dframe.index)
    cds = ColumnDataSource(data=dframe)

    plot.circle(x=xvar,
                y=yvar,
                color='COLOR',
                size=10,
                fill_alpha=0.5,
                source=cds)

    if kwargs['url'] is not None:
        taptool = plot.select(type=TapTool)
        website_loc = "https://en.wikipedia.org/wiki/@{0:s}"
        url_string = website_loc.format(kwargs['url'])
        taptool.callback = OpenURL(url=url_string)

    return plot
