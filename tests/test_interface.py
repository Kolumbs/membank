"""
Tests for membank.interface main API for library
"""
import datetime
from typing import NamedTuple
import os
from unittest import TestCase

import membank


# Test tables
class Dog(NamedTuple):
    """
    Simple example from README
    """
    breed: str
    color: str = "black"
    weight: float = 0


class UnsupportedType(NamedTuple):
    """
    Example with unsupported type
    """
    done: Dog


class Transaction(NamedTuple):
    """
    Example with pre post handling
    """
    amount: float
    description: str
    timestamp: datetime.datetime
    id: str = ""

    def add_id(self):
        """ads unique id to transaction"""
        return f"special_id:{self.description}"


class WrongDynamic(NamedTuple):
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
        booking = Transaction(50, "payment for buffer", datetime.datetime.now())
        memory.put(booking)
        new_booking = memory.get.transaction()
        self.assertEqual(booking.add_id(), new_booking.id)
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

    def test(self):
        """read and create memory"""
        memory = membank.LoadMemory()
        dog = Dog("red")
        memory.put(dog)
        memory.put(dog) # puts are idempotent
        new_dog = memory.get.dog()
        memory.put(new_dog) # one can put the got thing back
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(dog, i), getattr(new_dog, i))
        self.assertTrue(new_dog.id)

    def test_file_path_absolute(self):
        """create sqlite with file path"""
        cwd = os.getcwd()
        memory = membank.LoadMemory(f"sqlite://{cwd}/tests/test_database.db")
        memory.reset()
        old_dog = Dog("red")
        memory.put(old_dog)
        self.assertTrue(memory)
        new_dog = memory.get.dog()
        for i in ["breed", "color", "weight"]:
            self.assertEqual(getattr(old_dog, i), getattr(new_dog, i))

    def test_file_path_relative(self):
        """create sqlite with relative file path"""
        memory = membank.LoadMemory("sqlite://test_database.db")
        self.assertTrue(memory)


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
