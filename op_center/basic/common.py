import abc
import asyncio
import datetime
import functools
import hashlib
import json
import uuid


def get_real_function(f):
    while hasattr(f, '__wrapped__'):
        f = f.__wrapped__
    return f

def password_encode(password):
    return hashlib.sha1(password.encode()).hexdigest()


def gen_token():
    return uuid.uuid4().hex


class Now:

    def __init__(self):
        self.time = datetime.datetime.now()
        self.format = "%Y-%m-%d %H:%M:%S.%f"

    def instance(self):
        return self.time

    def string(self):
        return self.time.strftime(self.format)

    def timestamp(self):
        return self.time.timestamp()


class Object(metaclass=abc.ABCMeta):

    @property
    def meta(self):
        return self._meta

    @property
    def loop(self):
        return self._loop

    def __init__(self, meta: dict, loop=None):
        self._meta = meta
        self._loop = loop or asyncio.get_event_loop()
        self.__async_function_cache__ = {}


def object_cache(f):
    def get_cache_key(func, args, kwargs):
        s1 = hash(func)
        s2 = hash(frozenset(args))
        s3_keys = list(kwargs.keys())
        s3_keys.sort()
        s3 = hash(tuple([(k, kwargs[k]) for k in s3_keys]))
        return f"{s1}{s2}{s3}"

    @functools.wraps(f)
    async def wrapper(self: Object, *args, **kwargs):
        hash_key = get_cache_key(f, args, kwargs)
        if hash_key in self.__async_function_cache__:
            return self.__async_function_cache__[hash_key]
        result = await f(self, *args, **kwargs)
        self.__async_function_cache__[hash_key] = result
        return result

    return wrapper


class BaseJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Object):
            return obj.meta
        else:
            return json.JSONEncoder.default(self, obj)


serializer = functools.partial(json.dumps,
                               cls=BaseJsonEncoder,
                               ensure_ascii=False)
