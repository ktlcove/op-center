import logging
import unittest

from op_center.server import host_filter
from op_center.server.host_filter import HostFilterException
from test import async_run

logger = logging.getLogger(__name__)


class TestHostFilter(unittest.TestCase):

    @async_run
    async def setUp(self):
        self.target = host_filter.HostFilter(
            {
                "id": 0,
                "name": "test",
                "description": "test desc",
                "group_id": None,
                "filters": [
                    {"idc": {
                        "in": ["idc1", ],
                    }},
                    {"env": {
                        "is": "test",
                    }},
                    {"ip": {
                        "regexp": "^10\.0\.0\.[0-9]{1,3}$",
                        "in": {"10.0.0.64", "10.0.0.106"},
                    }}
                ]
            }
        )

        self.target_error = host_filter.HostFilter(
            {
                "id": 0,
                "name": "test",
                "description": "test desc",
                "group_id": None,
                "filters": [
                    {"not exist": {
                        "in": ["idc1", ],
                    }},
                    {"env": {
                        "is": "test",
                    }},
                    {"ip": {
                        "regexp": "^10\.0\.0\.[0-9]{1,2}$",
                        "in": ["10.0.0.64", "10.0.0.106"],
                    }}
                ]
            }
        )

        self.target_error2 = host_filter.HostFilter(
            {
                "id": 0,
                "name": "test",
                "description": "test desc",
                "group_id": None,
                "filters": [
                    {"idc": {
                        "not exist": ["idc1", ],
                    }},
                    {"env": {
                        "is": "env1",
                    }},
                    {"ip": {
                        "regexp": "^10\.0\.0\.[0-9]{1,2}$",
                        "in": {"10.0.0.64", "10.0.0.106"},
                    }}
                ]
            }
        )

    @async_run
    async def test_x(self):
        hosts = await self.target.get_hosts()
        self.assertEqual(len(hosts), 2)
        with self.assertRaises(HostFilterException):
            await self.target_error.get_hosts()

        with self.assertRaises(HostFilterException):
            await self.target_error2.get_hosts()


if __name__ == '__main__':
    unittest.main()
