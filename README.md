# PyIgor

PyIgor facilitates communication between Python and WaveMetrics Igor Pro, enabling seamless data and command exchange.

## Requirements

- **Igor Pro 7.0 or later:** Ensure you have Igor Pro 7.0 or a newer version installed.
- **HDF5 XOP:** Install the HDF5 XOP module. Detailed installation instructions are available in the "HDF5 installation" section under Igor Pro's help topics.
- **PyIgor Procedure File:** Download the `pyigor.ipf` file from [GitHub](https://github.com/chocolate-icecream/pyigor/blob/master/pyigor.ipf) and place it in the Igor Procedures folder for convenience.

## Installation

To install PyIgor, use the following pip command:

```bash
pip install pyigor
```

## Usage

Note: Ensure Igor Pro is running before executing these commands. If Igor Pro is not already running, the commands will start Igor Pro and pause until the process completes.

### Accessing Igor Pro from Python

Here’s how you can interact with Igor Pro using PyIgor:

```python
from pyigor import Connection
import numpy as np

# Establish a connection with Igor Pro
igor = Connection()

# Send a numpy array to Igor Pro
array = np.sin(np.linspace(0, 10, 100))
igor.put(array, "sinwave")

# Execute a command in Igor Pro
igor("sinwave += 1")

# Retrieve a wave from Igor Pro
wv = igor.get("sinwave")
print(wv.array)
```

### Accessing Python from Igor Pro

#### Preparing Python

```python
from pyigor import Connection

# Establish a connection
igor = Connection()

# Register a function callable from Igor Pro
@igor.function 
def myfunc(a):
    return a * a

# Keep the connection open; not required in interactive mode
igor.wait_done()
```

Use the `Connection(security_hole=True)` option to call any Python code from Igor Pro. This setting allows executing Python code through HTTP requests to `http://localhost/code` using `eval(code)`. **Important:** Use this option only if you understand the security implications.

#### Calling Python Functions from Igor Pro

Execute Python functions registered via PyIgor from Igor Pro:

```igorpro
print PyIgorCall("myfunc(10)")
```

## Security Note

When enabling `security_hole=True`, ensure your environment is secure and understand the risks associated with executing arbitrary code.



## Contributors

 A special thanks to the people who have contributed to this project:

- [@nlyamada](https://github.com/nlyamada) - Made compatible with Windows
