"""Tests for membank.interface main API for library."""
import dataclasses
from dataclasses import dataclass
import datetime

import membank
from tests import base as b


# Test tables
@dataclass
class Dog():
    """Simple example from README."""

    breed: str
    color: str = "black"
    weight: float = 0.0
    data: dict = dataclasses.field(default_factory=dict)
    picture: bytes = b''
    alive: bool = True
    aliases: list = dataclasses.field(default_factory=list)


@dataclass
class UpdatedDog():
    """Dog that is updated."""

    breed: str
    color: str = "black"


@dataclass
class Cat():
    """Cat example."""

    id: str = dataclasses.field(default=None, metadata={"key": True})
    color: str = "black"


@dataclass
class Transaction():
    """Example with pre post handling."""

    amount: float
    description: str
    timestamp: datetime.datetime = None
    id: str = dataclasses.field(default=None, metadata={"key": True})

    def __post_init__(self):
        """Add unique id to transaction."""
        if not self.timestamp:
            self.timestamp = datetime.datetime.now()
        if not self.id:
            self.id = f"special_id:{self.description}"


@dataclass
class Perforator():
    """Example with name attibute."""

    name: str


@b.add_memory
class CleanData(b.TestCase):
    """Testcase on clean_all_data function in Memory."""

    def test(self):
        """clean_all_data wipes data but not tables."""
        self.memory.put(Dog("Puli"))
        self.memory.clean_all_data()
        self.memory.get("dog")
        self.memory.put(Dog("Puli"))


@b.add_memory(b.DBPath.RELATIVE, reset=True)
class Operator(b.TestCase):
    """Testcases on comparison operators."""

    def test_equal(self):
        """Equality on name."""
        self.memory.put(Perforator("perforate"))
        self.assertTrue(self.memory.get(self.memory.perforator.name == "perforate"))


@b.add_memory(b.DBPath.RELATIVE, reset=True)
class Delete(b.TestCase):
    """Delete a memory item."""

    def test_delete(self):
        """Delete an item."""
        booking = Transaction(50, "delete transaction")
        self.memory.put(booking)
        self.assertTrue(self.memory.get.transaction(id=booking.id))
        self.memory.delete(booking)
        self.assertFalse(self.memory.get.transaction(id=booking.id))


@b.add_memory(b.DBPath.RELATIVE, reset=True)
class GetList(b.TestCase):
    """Testcase on getting list of items instead of single."""

    def setUp(self):
        """Add transactions as testdata."""
        super().setUp()
        for i in range(10):
            booking = Transaction(50 + i, f"list transaction {i}")
            self.memory.put(booking)

    def test_list(self):
        """Retrieve all items from one table."""
        bookings = self.memory.get("transaction")
        self.assertEqual(len(bookings), 10)
        for i, j in enumerate(bookings):
            self.assertEqual(j.amount, 50 + i)
            self.assertEqual(j.description, f"list transaction {i}")

    def test_operators(self):
        """Verify that comparison operators can be used."""
        today = datetime.datetime.now()
        bookings = self.memory.get(*(self.memory.transaction.timestamp <= today, ))
        self.assertEqual(len(bookings), 10)
        for i in bookings:
            self.assertTrue(i.timestamp <= today)

    def test_missing_table(self):
        """Operators with missing table should return None."""
        self.memory.get(self.memory.nonexisting.timestamp >= False)


@b.add_memory
class DynamicFields(b.TestCase):
    """Create memory structures with dynamic field generation."""

    def test(self):
        """Dynamic field must generate id."""
        booking = Transaction(50, "payment for buffer")
        self.memory.put(booking)
        new_booking = self.memory.get.transaction()
        self.assertEqual(booking.id, new_booking.id)
        self.assertEqual(booking.timestamp, new_booking.timestamp)
        self.memory.put(booking)

    def test_wrong_input(self):
        """Dynamic field with wrong input."""
        @dataclass
        class WrongDynamic():
            def add_id(self):
                return self
        with self.assertRaises(membank.GeneralMemoryError):
            self.memory.put(WrongDynamic)


@b.add_memory
class CreateRead(b.TestCase):
    """Create simple memory structure, add item and get it back."""

    def assert_equal(self, item1, item2):
        """Assert two dogs are equal."""
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(item1, i), getattr(item2, i))
        self.assertIn(str(item1)[:-1], str(item2))

    def test(self):
        """Read and create memory."""
        dog = Dog("Puli")
        self.memory.put(dog)
        self.memory.put(dog)  # puts are idempotent
        new_dog = self.memory.get.dog()
        self.assert_equal(dog, new_dog)
        self.memory.put(new_dog)  # one can put the got thing back
        self.assert_equal(dog, new_dog)

    def test_file_path_absolute(self):
        """Create sqlite with file path."""
        memory = membank.LoadMemory(b.DBPath.ABSOLUTE)
        memory.reset()
        old_dog = Dog("red")
        memory.put(old_dog)
        memory.put(old_dog)
        new_dog = memory.get.dog()
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(old_dog, i), getattr(new_dog, i))

    def test_file_path_relative(self):
        """Create sqlite with relative file path."""
        memory = membank.LoadMemory(b.DBPath.RELATIVE)
        self.assertTrue(memory)


class UpdateHandling(b.TestCase):
    """Do update existing field."""

    def test(self):
        """Create and update."""
        memory = membank.LoadMemory()
        memory.put(Transaction(6.5, "Small post to update"))
        booking = memory.get.transaction()
        self.assertEqual(booking.amount, 6.5)
        booking.amount = 6.6
        memory.put(booking)
        booking = memory.get.transaction()
        self.assertEqual(booking.amount, 6.6)


class UpdateWithDBChange(b.TestCase):
    """Do update with database schema changes."""

    def setUp(self):
        """Add memory and setup initial test data."""
        super().setUp()
        self.memory = membank.LoadMemory()
        self.dog = UpdatedDog("Puli")
        self.memory.put(self.dog)

    def tearDown(self):
        """Restore the dog to original state."""
        super().tearDown()
        global UpdatedDog

        @dataclass
        class UpdatedDog():
            """Version 2 for Dog."""

            breed: str
            color: str = "black"

    def test_update_changed(self):
        """Update item that is changed."""
        # pylint: disable=global-statement
        self.assertEqual(self.dog, self.memory.get.updateddog())
        global UpdatedDog

        @dataclass
        class UpdatedDog():
            """Version 2 for Dog."""

            breed: str
            new_field: str
            color: str = "black"
            weight: float = 0.0

        dog = UpdatedDog("NewPuli", "something")
        self.memory.put(dog)
        new_dog = self.memory.get.updateddog(breed="NewPuli")
        self.assertEqual(dog, new_dog)


class UpdateWithKey(b.TestCase):
    """Do update with database schema changes."""

    def test_update_changed_with_key(self):
        """Update item that is changed and has a key field."""
        global Cat
        cat = Cat("Ronalo")
        memory = membank.LoadMemory()
        memory.put(cat)

        @dataclass
        class Cat():
            """Version 2 with key field."""

            id: str = dataclasses.field(default=None, metadata={"key": True})
            breed: str = "unknown"

        cat = Cat("Romber")
        memory.put(cat)
        new_cat = memory.get.cat(id="Romber")
        self.assertEqual(cat, new_cat)
        self.assertEqual(new_cat.breed, "unknown")


class LoadMemoryErrorHandling(b.TestCase):
    """Handle errors on LoadMemory init."""

    def test_wrong_scheme(self):
        """Unrecognised scheme should fail."""
        with self.assertRaises(membank.errors.GeneralMemoryError):
            membank.LoadMemory(url="jumbo://www.zoozl.net")

    def test_wrong_path(self):
        """Invalid paths should fail."""
        with self.assertRaises(membank.errors.GeneralMemoryError):
            membank.LoadMemory(url="berkeleydb://:memory:")
        with self.assertRaises(membank.errors.GeneralMemoryError):
            membank.LoadMemory(url="sqlite://www.zoozl.net/gibberish")
        with self.assertRaises(membank.errors.GeneralMemoryError):
            membank.LoadMemory(url=dict(id="path"))


@b.add_memory
class PutMemoryErrorHandling(b.TestCase):
    """Handle errors on LoadMemory.put function."""

    def test_wrong_input(self):
        """Input should fail if not namedtuple instance."""
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put("blblbl")

        @dataclass
        class UnsupportedType():
            done: Dog
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(UnsupportedType)
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(Dog)
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(Dog(1))

    def test_reserved_name(self):
        """Input should fail if reserved name."""
        # pylint: disable=C0103,C0115,C0116
        @dataclass
        class __meta_dataclasses__():
            id: str
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(__meta_dataclasses__("ad"))

        @dataclass
        class Put():
            id: str
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(Put("ad"))


class GetMemoryErrorHandling(b.TestCase):
    """Handle errors on LoadMemory.get function."""

    def test_none_existing_table(self):
        """Input should raise error if not existing table."""
        memory = membank.LoadMemory(b.DBPath.RELATIVE)
        with self.assertRaises(membank.errors.GeneralMemoryError):
            memory.get.thisdoesnotexist()
        with self.assertRaises(membank.errors.GeneralMemoryError):
            memory.get("thisdoesnotexist")

    def test_attribute_error(self):
        """Fetching non existing attribute should fail."""
        memory = membank.LoadMemory()
        memory.put(Dog("lol"))
        with self.assertRaises(membank.errors.GeneralMemoryError) as error:
            memory.get(memory.dog.super_breed == "lol")
        self.assertIn("does not hold", str(error.exception))
        with self.assertRaises(membank.errors.GeneralMemoryError) as error:
            memory.get(breed="lol")
