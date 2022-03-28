"""
Tests for membank.interface main API for library
"""
import dataclasses as data
from dataclasses import dataclass
import datetime

import membank
from tests.base import TestCase


# Test tables
@dataclass
class Dog():
    """
    Simple example from README
    """
    breed: str
    color: str = "black"
    weight: float = 0.0


@dataclass
class Transaction():
    """
    Example with pre post handling
    """
    amount: float
    description: str
    timestamp: datetime.datetime = None
    id: str = data.field(default=None, metadata={"key": True})

    def __post_init__(self):
        """adds unique id to transaction"""
        if not self.timestamp:
            self.timestamp = datetime.datetime.now()
        if not self.id:
            self.id = f"special_id:{self.description}"

@dataclass
class Perforator():
    """
    Example with name attibute
    """
    name: str


class CleanData(TestCase):
    """
    Testcase on clean_all_data function in Memory
    """

    def setUp(self):
        self.memory = membank.LoadMemory()

    def test(self):
        """clean_all_data wipes data but not tables"""
        self.memory.put(Dog("Puli"))
        self.memory.clean_all_data()
        self.memory.get("dog")
        self.memory.put(Dog("Puli"))


class Operator(TestCase):
    """
    Testcases on comparison operators
    """

    def test_equal(self):
        """equality on name"""
        memory = membank.LoadMemory(self.relative_path)
        memory.put(Perforator("perforate"))
        self.assertTrue(memory.get(memory.perforator.name == "perforate"))


class Delete(TestCase):
    """
    Delete a memory item
    """

    def test_delete(self):
        """delete an item"""
        memory = membank.LoadMemory(self.relative_path)
        memory.reset()
        booking = Transaction(50, "delete transaction")
        memory.put(booking)
        self.assertTrue(memory.get.transaction(id=booking.id))
        memory.delete(booking)
        self.assertFalse(memory.get.transaction(id=booking.id))


class GetList(TestCase):
    """
    Testcase on getting list of items instead of single
    """

    def setUp(self):
        memory = membank.LoadMemory(self.relative_path)
        memory.reset()
        for i in range(10):
            booking = Transaction(50 + i, f"list transaction {i}")
            memory.put(booking)
        self.memory = memory

    def test_list(self):
        """retrieve all items from one table"""
        bookings = self.memory.get("transaction")
        self.assertEqual(len(bookings), 10)
        for i, j in enumerate(bookings):
            self.assertEqual(j.amount, 50 + i)
            self.assertEqual(j.description, f"list transaction {i}")

    def test_operators(self):
        """verify that comparison operators can be used"""
        today = datetime.datetime.now()
        bookings = self.memory.get(*(self.memory.transaction.timestamp <= today, ))
        self.assertEqual(len(bookings), 10)
        for i in bookings:
            self.assertTrue(i.timestamp <= today)

    def test_missing_table(self):
        """operators with missing table should return None"""
        self.memory.get(self.memory.nonexisting.timestamp >= False)


class DynamicFields(TestCase):
    """
    Create memory structures with dynamic field generation
    """

    def test(self):
        """dynamic field must generate id"""
        memory = membank.LoadMemory()
        booking = Transaction(50, "payment for buffer")
        memory.put(booking)
        new_booking = memory.get.transaction()
        self.assertEqual(booking.id, new_booking.id)
        self.assertEqual(booking.timestamp, new_booking.timestamp)
        memory.put(booking)

    def test_wrong_input(self):
        """dynamic field with wrong input"""
        memory = membank.LoadMemory()
        # pylint: disable=C0115,C0116
        @dataclass
        class WrongDynamic():
            def add_id(self):
                return self
        with self.assertRaises(membank.GeneralMemoryError):
            memory.put(WrongDynamic)


class CreateRead(TestCase):
    """
    Create simple memory structure, add item and get it back
    """

    def assert_equal(self, item1, item2):
        """asserts two dogs are equal"""
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(item1, i), getattr(item2, i))
        self.assertIn(str(item1)[:-1], str(item2))

    def test(self):
        """read and create memory"""
        memory = membank.LoadMemory()
        dog = Dog("Puli")
        memory.put(dog)
        memory.put(dog) # puts are idempotent
        new_dog = memory.get.dog()
        self.assert_equal(dog, new_dog)
        memory.put(new_dog) # one can put the got thing back
        self.assert_equal(dog, new_dog)

    def test_file_path_absolute(self):
        """create sqlite with file path"""
        memory = membank.LoadMemory(self.absolute_path)
        memory.reset()
        old_dog = Dog("red")
        memory.put(old_dog)
        memory.put(old_dog)
        new_dog = memory.get.dog()
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(old_dog, i), getattr(new_dog, i))

    def test_file_path_relative(self):
        """create sqlite with relative file path"""
        memory = membank.LoadMemory(self.relative_path)
        self.assertTrue(memory)


class UpdateHandling(TestCase):
    """
    Do update existing field
    """

    def test(self):
        """create and update"""
        memory = membank.LoadMemory()
        memory.put(Transaction(6.5, "Small post to update"))
        booking = memory.get.transaction()
        self.assertEqual(booking.amount, 6.5)
        booking.amount = 6.6
        memory.put(booking)
        booking = memory.get.transaction()
        self.assertEqual(booking.amount, 6.6)

class LoadMemoryErrorHandling(TestCase):
    """
    Handle errors on LoadMemory init
    """

    def test_wrong_scheme(self):
        """unrecognised scheme should fail"""
        with self.assertRaises(membank.interface.GeneralMemoryError):
            membank.LoadMemory(url="jumbo://www.zoozl.net")

    def test_wrong_path(self):
        """invalid paths should fail"""
        with self.assertRaises(membank.interface.GeneralMemoryError):
            membank.LoadMemory(url="berkeleydb://:memory:")
        with self.assertRaises(membank.interface.GeneralMemoryError):
            membank.LoadMemory(url="sqlite://www.zoozl.net/gibberish")
        with self.assertRaises(membank.interface.GeneralMemoryError):
            membank.LoadMemory(url=dict(id="path"))


class PutMemoryErrorHandling(TestCase):
    """
    Handle errors on LoadMemory.put function
    """

    def setUp(self):
        self.memory = membank.LoadMemory()

    def test_wrong_input(self):
        """input should fail if not namedtuple instance"""
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put("blblbl")
        # pylint: disable=C0115,C0116
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
        """input should fail if reserved name"""
        # pylint: disable=C0103,C0115,C0116
        @dataclass
        class __meta_dataclasses__():
            id: str
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(__meta_dataclasses__("ad"))
        # pylint: disable=C0115,C0116
        @dataclass
        class Put():
            id: str
        with self.assertRaises(membank.interface.GeneralMemoryError):
            self.memory.put(Put("ad"))


class GetMemoryErrorHandling(TestCase):
    """
    Handle errors on LoadMemory.get function
    """

    def test_none_existing_table(self):
        """input should return None if not existing table"""
        memory = membank.LoadMemory(self.relative_path)
        self.assertIsNone(memory.get.thisdoesnotexist())
        self.assertTrue(isinstance(memory.get("thisdoesnotexist"), list))

    def test_attribute_error(self):
        """fetching non existing attribute should fail"""
        memory = membank.LoadMemory()
        memory.put(Dog("lol"))
        with self.assertRaises(membank.interface.GeneralMemoryError) as error:
            memory.get(memory.dog.super_breed == "lol")
        self.assertIn("does not hold", str(error.exception))
        with self.assertRaises(membank.interface.GeneralMemoryError) as error:
            memory.get(breed="lol")
