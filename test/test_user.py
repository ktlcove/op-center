import logging
import unittest

from op_center.server import user
from test import async_run

logger = logging.getLogger(__name__)


class TestUser(unittest.TestCase):

    @async_run
    async def test_x(self):
        u = await user.User.login_by_password("local-admin", "admin")
        self.assertIsInstance(u, user.User)
        logger.info(u.meta)
        logger.info(await u.my_groups())
        logger.info(await u.my_basic_group())
        logger.info(await u.my_overall_permissions())
        logger.info(await u.my_group_private_permissions(1))

        u = await user.User.login_by_password("****", "****")
        self.assertIsInstance(u, user.User)
        logger.info(u.meta)
        logger.info(await u.my_groups())
        logger.info(await u.my_basic_group())
        logger.info(await u.my_overall_permissions())
        logger.info(await u.my_group_private_permissions(1))


if __name__ == '__main__':
    unittest.main()
