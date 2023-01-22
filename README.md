# PyIgor

PyIgor bridges between Python and WaveMetrics Igor Pro.

## Preparation

- Igor Pro 7.0 or later
- HDF5 XOP installation (See HDF5 installation in Igor Pro's help topics for the detail).
- Load pyigor.ipf (https://github.com/chocolate-icecream/pyigor/blob/master/pyigor.ipf, Put it into User Procedure folder for convenience).

## Usage

#### Accessing Igor Pro from Python

```python
from pyigor import Connection
import numpy as np

array = np.sin(np.linspace(0, 10, 100))

igor = Connection()
igor.put(array, "sinwave")

wv = igor.get("sinwave")
print(wv)
```

#### Accessing Python from Igor Pro

###### Preparation in Python

```python
from pyigor import Connection

igor = Connection()

@igor.function
def myfunc(a):
	return a*a

igor.wait_done()
```

###### Calling registered functions from Igor Pro

```
print PyIgorCall("myfunc(10)")
```

