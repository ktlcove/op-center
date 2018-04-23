import aiohttp

from op_center.basic import cfg
from op_center.other_system import ABCSystem, OtherSystemException


class CMDBResponseException(OtherSystemException):
    pass


class CMDB(ABCSystem):
    AUTH_HEADERS = {
        "username": cfg["other_system"]["cmdb"]["username"],
        "Authorization": "token {}".format(cfg["other_system"]["cmdb"]["token"])
    }
    SITE = cfg["other_system"]["cmdb"]["site"]
    TIMEOUT = cfg["other_system"]["cmdb"]["timeout"]

    @property
    def session(self):
        if not self._session:
            self._session = aiohttp.ClientSession(
                headers=self.AUTH_HEADERS)
        return self._session

    async def _parse_response(self, response):
        if response["ec"] != 0:
            raise CMDBResponseException(f"ec: {response['ec']}, em: {response['em']}")
        else:
            return response["data"]

    async def get_hosts(self):
        result = await self._request("GET",
                                     f"{self.SITE}/path/to/get/host",
                                     wait_timeout=60)
        return result
