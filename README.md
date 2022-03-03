# membank
Python library for storing data in persistent memory (sqlite, postgresql, berkeley db)
## goals
Provide interface to database storage that automates heavy lifting of database setup, migration, table definition, query construction.
## quick intro
### add items to persistent storage
```python
from membank import LoadMemory
from collections import namedtuple

memory = LoadMemory() # defaults to sqlite memory
Dog = namedtuple('Dog', ['color', 'size', 'breed'])
memory.create(Dog) # expects Python collections.namedtuple
memory.put.dog(Dog('brown')) # stores object into database
dog = memory.get.dog() # retrieves first object found as namedtuple
assert dog.color == 'brown'
```
### retrieve those after
```python
memory = LoadMemory() # to make this work in new process, use something else than sqlite memory
dog = memory.get.dog()
assert dog.color == 'brown'
```
