Installation
============

Requirements
------------

- Python 3.10 or higher
- No external runtime dependencies (only pydantic and msgpack)

Install from PyPI
-----------------

.. code-block:: bash

    pip install netconduit

Install from Source
-------------------

.. code-block:: bash

    git clone https://github.com/DarsheeeGamer/NetConduit.git
    cd NetConduit
    pip install -e .

Development Installation
------------------------

For development with testing and docs tools:

.. code-block:: bash

    pip install -e ".[dev,docs]"

Verify Installation
-------------------

.. code-block:: python

    import conduit
    print(conduit.__version__)  # 4.0.0

Dependencies
------------

**Runtime:**

- ``pydantic>=2.0`` - Data validation and serialization
- ``msgpack>=1.0`` - Binary serialization

**Development:**

- ``pytest`` - Testing framework
- ``sphinx`` - Documentation generation
