>NOTE: This ReadMe is unfinished and still in progress

# mcpacker
> Wrapper for [vberlier/mcpack](https://github.com/vberlier/mcpack), also requires python 3.7

```python
from mcpacker import DataPacker

pack = DataPacker('my_pack', 'My description.')

pack.dump()
```

## Installation

Using python 3.8 or high, it can be installed with ```pip```

_Currently only available from the TestPyPi instance of the Python Package Index_

```bash
pip install -i https://test.pypi.org/simple/ mcpacker
```

## Setting items

- When setting items, the pack's name will be used as the namespace when no namespace is given:

    ```python
    pack['say_hi'] = Function('say Hi!')
    ```
    is equivalent to
    ```python
    pack[f'{pack.name}:say_hi'] = Function('say Hi!')
    ```

## Data

> Introducing separation of code and data

Package will try to load [JSON](https://www.json.org/) data from ```./data/{pack.name}.json``` into ```pack.data```. If it fails, ```pack.data``` will be an empty dictionary.

Structure (each root item is optional):

- dependencies: list of other data packs upon which ```pack``` is based. [details](#data-pack-dependency-management)
- scoreboards: list of scoreboards
   - each scoreboard has the form: name criteria (display)
   - display is optional
- functions: list of function by relative path
- function_code: verbatim code for functions
- function_templates: (_in progress_)
- options: (_in progress_)
- recipe_advancement: (_in progress_)
- recipes: list of recipes

Example:
```json
{
    "dependencies": [
        "another_pack"
    ],
    "scoreboards": [
        "my_score dummy {\"text\":\"My Score\"}",
        "my_trigger trigger"
    ]
}
```

## Data Pack Dependency Management

> Details coming soon ...

(_in progress_)

## Functions

Functions ```load``` and ```tick``` are created automatically (if not empty)
