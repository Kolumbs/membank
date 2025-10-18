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
    data: dict = data.field(default_factory=dict)
    picture: bytes = b''
    aliases: list = data.field(default_factory=list)

@data.dataclass
class DogWithID():
    id: str = data.field(default=None, metadata={"key": True})
    breed: str
    color: str = "black"
    weight: float = 0
    data: dict = data.field(default_factory=dict)
    picture: bytes = b''
    alive: bool = True

memory = LoadMemory() # defaults to sqlite memory
memory.put(Dog('Puli')) # stores object into database
dog = memory.get.dog() # retrieves first object found
assert dog.breed == 'Puli'
dog.color = "white"
memory.put(dog) # be carefull you store another dog
dog = memory.put(DogWithID("AB1234", "Puli"))
dog = memory.get.dogwithid(id="AB1234")
dog.color = "white"
memory.put(dog) # now you update existing dog

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
### filter objects
```python
dog = memory.get.dog(breed='Labdrador')
assert dog.breed == 'Labrador'
```
