import asyncio
import logging

import aioredis
from aiohttp import web
from aiohttp_session import setup as session_setup
from aiohttp_session.redis_storage import RedisStorage

from op_center.basic import cfg
from op_center.server.http import router

logger = logging.getLogger(__name__)


async def middleware_404(_: web.Application, handler):
    async def middleware_handler(request):
        try:
            return await handler(request)
        except web.HTTPException as ex:
            if ex.status == 404:
                return web.json_response({"error": "Page Not Found", "code": 404},
                                         status=404)
            raise

    return middleware_handler


async def make_app(loop=None):
    logger.debug("create app start")
    loop = loop or asyncio.get_event_loop()
    app = web.Application(loop=loop, middlewares=[
        middleware_404,
    ])
    app.session_pool = await aioredis.create_pool(**cfg['http']['session']["link"])
    redis_storage = RedisStorage(app.session_pool,
                                 max_age=cfg["http"]["session"]["max_age"] * 24 * 3600)
    session_setup(app, redis_storage)
    router.setup(app)
    logger.debug("crate app success")
    return app


def main():
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(make_app(loop=loop))

    try:
        web.run_app(app,
                    host=cfg['http']["bind"],
                    port=cfg['http']['port'])
    finally:
        loop.close()
