import abc
import asyncio
import json

import aiohttp
import async_timeout

from op_center.basic import BasicException


class OtherSystemException(BasicException):
    pass


class OtherSystemResponseStatusException(OtherSystemException):
    pass


class OtherSystemResponseBodyLoadException(OtherSystemException):
    pass


class ABCSystem(metaclass=abc.ABCMeta):
    TIMEOUT = 10
    SITE = None

    @abc.abstractproperty
    def session(self) -> aiohttp.ClientSession:
        pass

    def __init__(self):
        self._session = None

    async def _request(self, method, url, wait_timeout=TIMEOUT, **kwargs):
        try:
            with async_timeout.timeout(wait_timeout):
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status < 200 or response.status >= 300:
                        raise OtherSystemResponseStatusException(f"request {url} response "
                                                                 f"status is `{response.status}`")
                    text_result = await response.text()
                    try:
                        result = json.loads(text_result)
                    except json.decoder.JSONDecodeError as e:
                        raise OtherSystemResponseBodyLoadException(f"json.loads body: `{text_result}` "
                                                                   f"raise an error: {e}")
                    return await self._parse_response(result)
        except asyncio.TimeoutError as e:
            print(method, url, wait_timeout, kwargs)
            raise e

    @abc.abstractmethod
    async def _parse_response(self, response):
        pass

    def __del__(self):
        asyncio.ensure_future(self.session.close())
