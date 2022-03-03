# membank
Python library for storing data in persistent memory (sqlite, postgresql, berkeley db)
## usage
>>> memory = LoadMemory() # defaults to sqlite memory
>>> Dog = namedtuple('Dog', ['color', 'size', 'breed'])
>>> memory.create(Dog) # expects Python collections.namedtuple
>>> memory.set.dog(Dog('brown')) # stores object into database
>>> memory.get.dog() # retrieves all objects as tuple

... new process ...
>>> memory = LoadMemory() # this works unless sqlite memory is used before
>>> memory.get.dog()
