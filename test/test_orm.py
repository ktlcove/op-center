import unittest

from op_center.server import orm
from test import async_run


class TestABCDB(unittest.TestCase):
    class Sample(orm.ABCOrm):
        TABLE = orm.t.g

    @async_run
    async def setUp(self):
        self.target = self.Sample()

    @async_run
    async def test_x(self):
        count = await self.target.count(orm.t.g.name == "test")
        self.assertEqual(count, 0)
        c_result = await self.target.create(name="test")
        self.assertIsInstance(c_result, int)
        r_result = await self.target.query(orm.t.g.name == "test")
        self.assertEqual(len(r_result), 1)
        self.assertIsInstance(r_result[0], dict)
        await self.target.query_update(orm.t.g.name == "test", description="test")
        count = await self.target.count(orm.t.g.name == "test")
        self.assertEqual(count, 1)
        exists = await self.target.exists(orm.t.g.name == "test")
        self.assertTrue(exists)
        with self.assertRaises(Exception):
            await self.target.only_or_raise(orm.t.g.name == "not exist")
        item = await self.target.only_or_none(orm.t.g.name == "test")
        self.assertIsInstance(item, dict)
        d_result = await self.target.query_delete(orm.t.g.name == "test")
        self.assertIsNone(d_result)
        r_result = await self.target.query(orm.t.g.name == "test")
        self.assertEqual(len(r_result), 0)
        exists = await self.target.exists(orm.t.g.name == "test")
        self.assertFalse(exists)

    @async_run
    async def tearDown(self):
        await self.target.query_delete(orm.t.g.name == "test")


class TestGroup(unittest.TestCase):

    @async_run
    async def setUp(self):
        self.target = orm.Group()
        await self.target.create(name="test1")
        self.group = await self.target.only_or_none(orm.t.g.name == "test1")

    @async_run
    async def test_x(self):
        print(self.group)

    @async_run
    async def tearDown(self):
        await self.target.query_delete(orm.t.g.name == "test1")


if __name__ == '__main__':
    unittest.main()
