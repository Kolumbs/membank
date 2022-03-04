# membank
Python library for storing data in persistent memory (sqlite, postgresql, berkeley db)
## goals
Provide interface to database storage that automates heavy lifting of database setup, migration, table definition, query construction.
## quick intro
### add items to persistent storage
```python
from typing import NamedTuple

from membank import LoadMemory

class Dog(NamedTuple):
    breed: str
    color: str = "black"
    weight: float = 0

memory = LoadMemory() # defaults to sqlite memory
memory.put.dog(Dog('Puli')) # stores object into database
dog = memory.get.dog() # retrieves first object found as namedtuple
assert dog.breed == 'Puli'
```
### retrieve those after
```python
memory = LoadMemory() # to make this work in new process, don't use sqlite memory
dog = memory.get.dog()
assert dog.color == 'black'
```
