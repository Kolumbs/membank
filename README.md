# membank
Python library for storing data in persistent memory (sqlite, postgresql, berkeley db)
## goals
Provide interface to database storage that automates heavy lifting of database setup, migration, table definition, query construction.
## quick intro
### add items to persistent storage
```python
import dataclasses as data # Python standard library

from membank import LoadMemory

@data.dataclass
class Dog():
    breed: str
    color: str = "black"
    weight: float = 0

memory = LoadMemory() # defaults to sqlite memory
memory.put(Dog('Puli')) # stores object into database
dog = memory.get.dog() # retrieves first object found
assert dog.breed == 'Puli'
```
### retrieve those after
```python
memory = LoadMemory() # to make this work in new process, don't use sqlite memory
dog = memory.get.dog() # get first found or None
assert dog.color == 'black'
dogs = memory.get("dog") # always returns list (empty or with items)
assert len(dogs) >= 0
```
### editing returned objects
```python
dog = memory.get.dog()
dog.breed = 'Labdrador'
memory.put(dog) # stores edited object back
```
