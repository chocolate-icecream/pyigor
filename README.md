# PyIgor

PyIgor bridges between Python and WaveMetrics Igor Pro.

## Preparation

- Igor Pro 7.0 or later
- HDF5 XOP installation (See HDF5 installation in Igor Pro's help topics for the detail).
- Load pyigor.ipf (https://github.com/chocolate-icecream/pyigor/blob/master/pyigor.ipf).

  Putting it in the Igor Procedures folder is very convenient.

## Usage

#### Accessing Igor Pro from Python

```python
from pyigor import Connection
import numpy as np

igor = Connection()

### Sending an array to Igor Pro
array = np.sin(np.linspace(0, 10, 100))
igor.put(array, "sinwave")

### Executing a command in Igor Pro
igor("sinwave += 1")

### Getting a wave from Igor Pro
wv = igor.get("sinwave")
print(wv.array)
```

#### Accessing Python from Igor Pro

###### Preparation in Python

```python
from pyigor import Connection

igor = Connection()

### @igor.function decorator makes the function callable from Igor Pro.
@igor.function 
def myfunc(a):
	return a*a

igor.wait_done() # Just to prevent the program quit. You don't need it in the interactive mode.
```

By using Connection(security_hole=True), you can call any Python code. Meanwhile, this option makes it possible to execute any Python code by HTTP requests: http://localhost/code -> `eval(code)`. Do not use unless you are sure of it.

###### Calling registered functions from Igor Pro

```
print PyIgorCall("myfunc(10)")
```
