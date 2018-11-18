# -*- coding: utf-8 -*-
"""Functions to creating interactive plots from Wikipedia data.
"""

from bokeh.models import OpenURL, TapTool
from bokeh.palettes import viridis
from bokeh.plotting import figure, show, output_notebook, ColumnDataSource

import pandas as pd
import numpy as np

output_notebook()

__version__ = 1


def create_figure(df, x, y, color=None, url=None,
                  title='', x_axis_label=None, y_axis_label=None,
                  nsizes=25):
    """Creates an interactive plot from a pandas data frame.
    
    Args:
        df: A pandas data frame.
        x: Name of the x-variable.
        y: Name of the y-variable.
        color: Optional name of the color variable.
        url: Optional name of the url variable.
        title: String giving the title of the plot.
        x_axis_label: String to label to the x-axis with.
        y_axis_label: String to label to the y-axis with.
        nsizes: Maximum number of colors to include in continuous plot.
    Returns:
        A bokeh plot object.
    """
    cnames = list(set(df.columns) - set([x, y, url]))
    tooltips = [(x, "@{0:s}".format(x)) for x in cnames]
    
    if x_axis_label is None:
        x_axis_label = x
    if y_axis_label is None:
        y_axis_label = y
        
    p = figure(plot_width=950,
               plot_height=600,
               tooltips=tooltips,
               tools="hover,pan,wheel_zoom,reset,tap",
               toolbar_location="below",
               toolbar_sticky=True,
               active_scroll='wheel_zoom',
               title=title,
               x_axis_label=x_axis_label,
               y_axis_label=y_axis_label)

    c = "#31AADE"
    if color is not None:
        num_col = np.issubdtype(df[color].dtype, np.number)
        if num_col and len(set(df[color])) > nsizes:
            codes = pd.qcut(df[color].values, nsizes, duplicates='drop').codes
        else:
            codes = pd.Categorical(df[color]).codes
        pal = viridis(np.max(codes) + 1)
        c = [pal[xx] for xx in codes]
    
    df = df.copy(deep=True)
    df['COLOR'] = pd.Series(c, index=df.index)
    cds=ColumnDataSource(data=df)
    
    p.circle(x=x,
             y=y,
             color='COLOR',
             size=10,
             fill_alpha=0.5,
             source=cds)
    
    if url is not None:
        taptool = p.select(type=TapTool)
        url_string = "https://en.wikipedia.org/wiki/@{0:s}".format(url)
        taptool.callback = OpenURL(url=url_string)

    return p