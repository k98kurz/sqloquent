import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import simplesqlorm
from simplesqlorm import classes, errors, interfaces, relations, migration