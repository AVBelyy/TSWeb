"""Python 2/3 compability code"""

import sys

if sys.version_info[0] == 2:
    xrange = xrange
else:
    xrange = range
