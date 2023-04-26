# coding: utf-8
"""Main package for humanize."""
from ..humanize.filesize import naturalsize
from ..humanize.i18n import activate, deactivate, decimal_separator, thousands_separator
from ..humanize.number import apnumber, clamp, fractional, intcomma, intword, metric, ordinal, scientific
from ..humanize.time import naturaldate, naturalday, naturaldelta, naturaltime, precisedelta
# try:
#     import importlib.metadata as importlib_metadata
# except ImportError:
#     import importlib_metadata
# __version__ = importlib_metadata.version(__name__)
__all__ = ['__version__', 'activate', 'apnumber', 'clamp', 'deactivate', 'decimal_separator', 'fractional', 'intcomma', 'intword', 'metric', 'naturaldate', 'naturalday', 'naturaldelta', 'naturalsize', 'naturaltime', 'ordinal', 'precisedelta', 'scientific', 'thousands_separator']
