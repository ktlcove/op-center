import abc
import asyncio
import logging
import uuid

from aiohttp import web
from aiohttp_session import get_session

from op_center.basic import serializer, BasicException
from op_center.server import user, controller
from op_center.server.http import HttpException

logger = logging.getLogger(__name__)


class ViewException(HttpException):
    pass


class ViewArgsException(ViewException):
    code = 400


class LoginRequired(ViewException):
    code = 403


null_args = object()


class RequiredDict(dict):
    def get(self, k, default=null_args, required=False, choices=None):
        result = super().get(k, default)
        if choices:
            if result not in choices:
                raise ViewArgsException(f"arg {k} must in {choices}")
            return result
        if required:
            if result is null_args:
                raise ViewArgsException(f"arg {k} must give a value")
        if result is null_args:
            return None
        else:
            return result


async def json_request_prepare(self: web.View):
    if self.request.method.upper() in self.request.POST_METHODS:
        if await self.request.text():
            try:
                self.request.POST = RequiredDict(await self.request.json())
            except Exception:
                raise ViewArgsException("json decode error")
        else:
            self.request.POST = RequiredDict()
    else:
        self.request.POST = RequiredDict()


async def multiform_or_json_request_prepare(self: web.View):
    if self.request.method.upper() in self.request.POST_METHODS:
        if self.request.content_type and self.request.content_type.lower() == "application/json":
            await json_request_prepare(self)
        else:
            self.request.POST = RequiredDict(await self.request.post())
    else:
        self.request.POST = RequiredDict()


class ABCView(web.View, metaclass=abc.ABCMeta):
    """
    function run order is
        1. call functions which name in __before_iter__ one by one
        2. call super.__iter__
            super__iter__ try to call function self.request.method
            if not found method will raise HttpMethodNotAllowError
        in step 1 and step 2
            when a function return a response
            return this response to user
            call on_finish
            call on_close
    """

    def __init__(self, request):
        super().__init__(request)
        self.session = None
        self._log_id = uuid.uuid4().hex
        self.user = None
        self.url_args = RequiredDict(self.request.match_info)

    __before_iter__ = ["check_session", "prepare", "login", "initialize"]

    async def check_session(self):
        self.session = await get_session(self.request)

    @abc.abstractmethod
    async def response(self, code=0, data=None, status=200, error=None, **kwargs):
        """
        base return function must accept status, error kwargs
        """
        pass

    @abc.abstractmethod
    async def prepare(self):
        pass

    @abc.abstractmethod
    async def login(self):
        pass

    async def initialize(self):
        pass

    async def permission_check(self):
        pass

    async def on_finish(self):
        pass

    async def on_close(self):
        pass

    @asyncio.coroutine
    def __iter__(self):
        result = None
        request_body = yield from self.request.text()
        logger.debug(
            """receive request:<id: {}> <"{} {}"> <match_info: {}> <query: {}> <body:{}> <header: {}>""".format(
                self._log_id, self.request.method, self.request.url, dict(self.request.match_info),
                dict(self.request.query), request_body, dict(self.request.headers), ))
        try:
            for func_name in self.__before_iter__:
                func = getattr(self, func_name)
                result = yield from func()
                if result:
                    break
            if not result:
                result = yield from super().__iter__()
            yield from self.on_finish()
            yield from self.on_close()
        except BasicException as e:
            result = yield from self.response(code=e.code, error=f"{e.type}: {e.msg}")
        except Exception as e:
            logger.critical("unknown error occur in view: {}".format(e.args), exc_info=True)
            result = yield from self.response(status=500, code=500, error=str(e))
        if not result:
            result = yield from self.response(status=500, code=500, error="not response return")
        if not isinstance(result, web.StreamResponse):
            logger.critical("code error: result of request is not a response instance")
            result = yield from self.response(status=500, code=500,
                                              error="code error: result of request is not a response instance")

        # web socket log
        #
        # try:
        #     if not hasattr(result, "body"):
        #         logger.debug("""<id: {}> <response_header: {}> <response_status: {}> (no body)""". \
        #                      format(_id, dict(result.headers), result.status))
        #         return result
        #     if 'deflate' in result.headers.get('content-encoding', ''):
        #         logger.debug("""<id: {}> <response_header: {}> <response_status: {}> <response_body: {}>""". \
        #                      format(_id, dict(result.headers), result.status, zlib.decompress(result.body)))
        #     else:
        #         logger.debug("""<id: {}> <response_header: {}> <response_status: {}> <response_body: {}>""". \
        #                      format(_id, dict(result.headers), result.status, result.text))
        # except Exception:
        #     try:
        #         logger.debug("""<id: {}> <response_header: {}> <response_status: {}> <response_body: {}>""". \
        #                      format(_id, dict(result.headers), result.status, result.body))
        #     except Exception:
        #         logger.critical("""base view logger module raise a critical error !!!""")
        return result


class ABCOpCenterView(ABCView):
    base_return_format = {
        "code": 0,
        "data": None,
        "error": None,
        "_id": None,
    }

    def __init__(self, request):
        super().__init__(request)
        self.controller = None

    async def prepare(self):
        await multiform_or_json_request_prepare(self)
        logger.debug(f"request.POST {self.request.POST}")
        logger.debug(f"request.query {self.request.query}")

    async def initialize(self):
        if self.user is user.anonymous:
            raise LoginRequired("user cant be anonymous, login first")
        self.controller = controller.Controller(self.user)

    async def response(self, code=0, data=None, status=200, error=None, **kwargs):
        return web.json_response(data={
            "code": code,
            "data": data,
            "error": error,
            "_log_id": self._log_id,
            **kwargs,
        }, status=status, dumps=serializer, content_type="application/json")

    async def login(self):
        try:
            self.user = await user.User.login_by_session(self.session)
            logger.debug(f"after session login user is {self.user}")
        except BasicException as e:
            return await self.response(code=403, error=f"{e.type}: {e.msg}")

        token = self.request.headers.get("X-Auth-Token", None)
        #     raise PrisonViewException("X-Auth-Token or X-Auth-Password header required")
        if token is not None:
            self.user = await user.User.login_by_token(token) or self.user
        logger.debug(f"after token login token({token}) user is {self.user}")
        if not self.user:
            self.user = user.anonymous
        logger.debug(f"latest self.user = {self.user}")
