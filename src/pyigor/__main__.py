from .pyigor import Connection, Wave

import code
import os
import math
import glob
import numpy as np
import pandas as pd

igor = Connection()
print("Preloaded objects: igor")
print("Preloaded modules: os, math, glob, numpy as np, pandas as pd")
code.interact(local=locals())