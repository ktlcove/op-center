import asyncio
import logging

from op_center.basic import USER_TYPE_LDAP, password_encode, USER_TYPE_LOCAL, object_cache, PMS_TYPE_PRIVATE
from op_center.server import ServerException
from op_center.server import orm
from op_center.server.ldap import ldap
from op_center.server.orm import t

logger = logging.getLogger(__name__)


class UserException(ServerException):
    pass


class UserNotFound(UserException):
    pass


class UserLoginFailed(UserException):
    pass


class User(orm.OrmObject):
    __ORM__ = orm.User

    @property
    def _group_orm(self):
        if not self.__group_orm:
            self.__group_orm = orm.Group(session=self.orm.session)
        return self.__group_orm

    def __init__(self, meta, loop=None, orm_session=None):
        super().__init__(meta, loop=loop, orm_session=orm_session)
        self.__group_orm = None

    def __str__(self):
        return self.meta["name"]

    @classmethod
    async def login_by_password(cls, username: str, password: str, orm_session=None):
        orm_session = orm_session or orm.DBSession()
        orm_instance = cls.__ORM__(session=orm_session)
        meta = await orm_instance.only_or_none(t.u.name == username)
        if not meta:
            raise UserNotFound(f"user(name={username}) not found")
        if meta['type'] == USER_TYPE_LDAP and await ldap.auth(username, password) or \
                meta['type'] == USER_TYPE_LOCAL and password_encode(password) == meta['password']:
            return cls({k: v for k, v in meta.items() if k != "password"},
                       orm_session=orm_session)
        else:
            raise UserLoginFailed("password error")

    @classmethod
    async def login_by_token(cls, token: str, orm_session=None):
        orm_session = orm_session or orm.DBSession()
        orm_instance = cls.__ORM__(session=orm_session)
        meta = await orm_instance.only_or_none(t.u.token == token)
        if not meta:
            raise UserLoginFailed(f"login failed")
        else:
            return cls({k: v for k, v in meta.items() if k != "password"},
                       orm_session=orm_session)

    @classmethod
    async def login_by_session(cls, session, orm_session=None):
        logger.debug(session)
        name = session.get("name", None)
        if name:
            orm_session = orm_session or orm.DBSession()
            orm_instance = cls.__ORM__(session=orm_session)
            meta = await orm_instance.only_or_none(t.u.name == name)
            if meta:
                return User(meta, orm_session=orm_session)
            else:
                logger.warning(f"user(name={name}) not found, but session exist")
        return None

    @property
    def name(self):
        return self.meta["name"]

    @object_cache
    async def my_groups(self):
        return await self.orm.get_groups(user_id=self.meta["id"])

    @object_cache
    async def my_basic_group(self):
        return await self.orm.get_basic_group(user_id=self.meta["id"])

    async def my_basic_group_id(self):
        return (await self.my_basic_group())["id"]

    @object_cache
    async def my_overall_permissions(self):
        return await self.orm.get_overall_permissions(user_id=self.meta["id"])

    @object_cache
    async def my_group_private_permissions(self, group_id):
        g_character = await self.orm.get_user_group_character(self.meta["id"], group_id)
        logger.debug(g_character)
        if not g_character:
            raise UserException(f"{group_id} is not your group")
        result = await self._group_orm.get_permissions(
            orm.t.gp.character <= g_character,
            group_id=group_id, type=PMS_TYPE_PRIVATE)
        return {r["permission"] for r in result}


anonymous = User(
    asyncio.get_event_loop().run_until_complete(
        orm.User().only_or_raise(t.u.name == "anonymous")))
