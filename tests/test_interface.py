"""
Tests for membank.interface main API for library
"""
import dataclasses as data
from dataclasses import dataclass
import datetime
import os
from unittest import TestCase

import membank


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
class UnsupportedType():
    """
    Example with unsupported type
    """
    done: Dog


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
        """ads unique id to transaction"""
        if not self.timestamp:
            self.timestamp = datetime.datetime.now()
        if not self.id:
            self.id = f"special_id:{self.description}"


@dataclass
class WrongDynamic():
    """
    Example with wrong dynamic field
    """

    def add_id(self):
        """ads unique id"""
        return self


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
        cwd = os.getcwd()
        memory = membank.LoadMemory(f"sqlite://{cwd}/tests/test_database.db")
        memory.reset()
        old_dog = Dog("red")
        memory.put(old_dog)
        memory.put(old_dog)
        new_dog = memory.get.dog()
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(old_dog, i), getattr(new_dog, i))

    def test_file_path_relative(self):
        """create sqlite with relative file path"""
        memory = membank.LoadMemory("sqlite://tests/test_database.db")
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

    def test_wrong_input(self):
        """input should fail if not namedtuple instance"""
        memory = membank.LoadMemory()
        with self.assertRaises(membank.interface.GeneralMemoryError):
            memory.put("blblbl")
        with self.assertRaises(membank.interface.GeneralMemoryError):
            memory.put(UnsupportedType)
        with self.assertRaises(membank.interface.GeneralMemoryError):
            memory.put(Dog)
        with self.assertRaises(membank.interface.GeneralMemoryError):
            memory.put(Dog(1))


class GetMemoryErrorHandling(TestCase):
    """
    Handle errors on LoadMemory.get function
    """

    def test_none_existing_table(self):
        """input should return None if not existing table"""
        memory = membank.LoadMemory("sqlite://tests/test_database.db")
        self.assertIsNone(memory.get.thisdoesnotexist())
