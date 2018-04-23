import abc
import asyncio
import concurrent.futures
import functools
import logging

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from op_center.basic import cfg, gen_token, password_encode, PMS_TYPE_OVERALL
from op_center.server import ServerException
from op_center.server import table, Object

logger = logging.getLogger(__name__)


class OrmException(ServerException):
    pass


class SqlException(OrmException):
    pass


class QueryResultException(OrmException):
    pass


engine = sa.create_engine("mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8".format_map(cfg["db"]),
                          pool_size=20, pool_pre_ping=True)
DBSession = sessionmaker(bind=engine, autoflush=True, autocommit=False)


class t:
    u = table.User
    g = table.Group
    gp = table.GroupPermission
    h = table.Host
    hf = table.HostFilter
    wf = table.Workflow
    optr = table.Operator
    optn = table.Operation
    tsk = table.Task


class ABCOrm(metaclass=abc.ABCMeta):
    TABLE = None
    PK = "id"

    SESSION_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=10,
                                                             thread_name_prefix="db-executor")

    @property
    def session(self):
        return self._session

    def __init__(self, session=None):
        self._session = session or DBSession()

    def __del__(self):
        self.session.close()

    async def _execute(self, *fs):
        def mf():
            result = None
            for f in fs:
                result = f()
            self.session.commit()
            return result

        return await asyncio.get_event_loop().run_in_executor(self.SESSION_EXECUTOR, mf)

    @staticmethod
    def _f(f, *args, **kwargs):
        return functools.partial(f, *args, **kwargs)

    def gen_query_columns(self, columns: list):
        return columns or list(self.TABLE._sa_class_manager.values())

    def op_create(self, **kwargs):
        obj = self.TABLE()
        for k, v in kwargs.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        self.session.add(obj)
        self.session.flush()
        result = getattr(obj, self.PK)
        logger.debug(f"create instance ok result {self.PK} is: {result}")
        return result

    def op_query_delete(self, *conditions):
        self.session.query(self.TABLE).filter(*conditions).delete(synchronize_session="fetch")

    def op_query_update(self, *conditions, **kwargs):
        self.session.query(self.TABLE).filter(*conditions).update(kwargs, synchronize_session="fetch")

    def op_query(self, *conditions, limit=None, columns=None):
        sql = self.session.query(*self.gen_query_columns(columns)).filter(*conditions)
        if limit:
            sql = sql.limit(limit)
        return [r._asdict() for r in sql.all()]

    def op_count(self, *conditions):
        return self.session.query(getattr(self.TABLE, self.PK)).filter(*conditions).count()

    def op_only_or_raise(self, *conditions, columns=None):
        count = self.op_count(*conditions)
        if count != 1:
            raise QueryResultException(f"acquire 1 row {count} found")
        return self.op_query(*conditions, columns=columns)[0]

    def op_only_or_none(self, *conditions, columns=None):
        try:
            return self.op_only_or_raise(*conditions, columns=columns)
        except QueryResultException:
            return None

    async def create(self, **kwargs):
        return await self._execute(self._f(self.op_create, **kwargs))

    async def exists(self, *conditions):
        return await self.count(*conditions) != 0
        # return await self._execute(self._f(self.op_exists, *conditions))

    async def not_exist_or_raise(self, *conditions):
        if await self.exists(*conditions):
            raise OrmException("target already exist")
        return True

    async def query_delete(self, *conditions):
        return await self._execute(self._f(self.op_query_delete, *conditions))

    async def query_update(self, *conditions, **kwargs):
        return await self._execute(self._f(self.op_query_update, *conditions, **kwargs))

    async def query(self, *conditions, columns=None):
        return await self._execute(self._f(self.op_query, *conditions, columns=columns))

    async def count(self, *conditions):
        return await self._execute(self._f(self.op_count, *conditions))

    async def only_or_raise(self, *conditions, columns=None):
        return await self._execute(self._f(self.op_only_or_raise, *conditions, columns=columns))

    async def only_or_none(self, *conditions, columns=None):
        return await self._execute(self._f(self.op_only_or_none, *conditions, columns=columns))


class User(ABCOrm):
    TABLE = table.User

    def op_create(self, *, basic_group_character, **kwargs):
        if "password" in kwargs and kwargs["password"] is not None:
            kwargs["password"] = password_encode(kwargs["password"])
        kwargs['token'] = gen_token()
        new_user_id = super().op_create(**kwargs)
        relation = table.UserGroupRelation(group_id=kwargs["basic_group_id"],
                                           character=basic_group_character,
                                           user_id=new_user_id)
        self.session.add(relation)
        self.session.flush()
        return new_user_id

    def op_join_group(self, user_id, *, group_id=None, character=None):
        relation = table.UserGroupRelation(group_id=group_id,
                                           character=character,
                                           user_id=user_id)
        self.session.add(relation)
        self.session.flush()

    def op_get_groups(self, *conditions, user_id):
        self.op_only_or_raise(self.TABLE.id == user_id)
        query = self.session.query(table.UserGroupRelation.group_id,
                                   table.UserGroupRelation.character,
                                   table.Group.name).select_from(table.UserGroupRelation). \
            join(table.Group, table.UserGroupRelation.group_id == table.Group.id). \
            filter(table.UserGroupRelation.user_id == user_id). \
            filter(*conditions)
        return [r._asdict() for r in query.all()]

    def op_get_basic_group(self, user_id=None):
        self.op_only_or_raise(self.TABLE.id == user_id)
        return self.session.query(table.Group.id,
                                  table.Group.name,
                                  table.Group.description,
                                  table.UserGroupRelation.character,
                                  table.Group.c_time,
                                  table.Group.m_time). \
            select_from(table.Group). \
            join(table.User, table.Group.id == table.User.basic_group_id). \
            join(table.UserGroupRelation, table.UserGroupRelation.group_id == table.Group.id). \
            filter(table.User.id == user_id,
                   table.UserGroupRelation.user_id == user_id).one()._asdict()

    def op_get_user_group_character(self, user_id, group_id):
        result = self.session.query(table.UserGroupRelation.character). \
            filter(table.UserGroupRelation.user_id == user_id,
                   table.UserGroupRelation.group_id == group_id). \
            one_or_none()
        if result:
            return result.character
        return None

    def op_get_overall_permissions(self, user_id=None):
        query = self.session.query(table.GroupPermission.permission). \
            join(table.UserGroupRelation, table.UserGroupRelation.group_id == table.GroupPermission.group_id). \
            filter(table.UserGroupRelation.user_id == user_id,
                   table.GroupPermission.type == PMS_TYPE_OVERALL,
                   table.UserGroupRelation.character >= table.GroupPermission.character).distinct()
        return {r.permission for r in query.all()}

    async def get_basic_group(self, user_id=None):
        return await self._execute(self._f(self.op_get_basic_group, user_id=user_id))

    async def get_groups(self, *conditions, user_id):
        return await self._execute(self._f(self.op_get_groups, *conditions, user_id=user_id))

    async def get_group_ids(self, *conditions, user_id):
        groups = await self.get_groups(*conditions, user_id=user_id)
        return [g["group_id"] for g in groups]

    async def get_overall_permissions(self, user_id=None):
        return await self._execute(self._f(self.op_get_overall_permissions,
                                           user_id=user_id))

    async def get_user_group_character(self, user_id, group_id):
        return await self._execute(self._f(self.op_get_user_group_character,
                                           user_id=user_id,
                                           group_id=group_id))

    async def join_group(self, user_id, *, group_id=None, character=None):
        return await self._execute(self._f(self.op_join_group,
                                           user_id=user_id,
                                           group_id=group_id,
                                           character=character))


class Group(ABCOrm):
    TABLE = table.Group

    def op_get_permissions(self, *conditions, group_id, type):
        self.op_only_or_raise(self.TABLE.id == group_id)
        result = self.session.query(table.GroupPermission.permission,
                                    table.GroupPermission.character,
                                    table.GroupPermission.type). \
            select_from(table.GroupPermission). \
            join(self.TABLE, self.TABLE.id == table.GroupPermission.group_id). \
            filter(self.TABLE.id == group_id,
                   table.GroupPermission.type == type). \
            filter(*conditions).all()
        return [r._asdict() for r in result]

    def op_set_or_update_permissions(self, group_id=None, type=None, *, ps: list):
        group = self.op_only_or_raise(self.TABLE.id == group_id)
        eps = self.op_get_permissions(group_id=group_id, type=type)
        eps_p_dict = {i["permission"]: {"character": i["character"]} for i in eps}
        for item in ps:
            # {character: xxx, permission: xxx}
            if item["permission"] not in eps_p_dict:
                new_p = table.GroupPermission(group_id=group["id"],
                                              type=type,
                                              permission=item["permission"],
                                              character=item["character"])
                self.session.add(new_p)
            else:
                # item["permission"] already in check character
                if item["character"] != eps_p_dict[item["permission"]]["character"]:
                    # character update
                    self.session.query(table.GroupPermission). \
                        filter(table.GroupPermission.group_id == group["id"],
                               table.GroupPermission.type == type,
                               table.GroupPermission.permission == item["permission"]). \
                        update({"character": item["character"]},
                               synchronize_session="fetch")
        self.session.flush()

    def op_query_delete_permissions(self, *conditions, group_id, type):
        self.session.query(table.GroupPermission). \
            select_from(table.GroupPermission). \
            join(self.TABLE, self.TABLE.id == table.GroupPermission.group_id). \
            filter(self.TABLE.id == group_id,
                   table.GroupPermission.type == type). \
            filter(*conditions).delete(synchronize_session="fetch")

    async def get_permissions(self, *conditions, group_id, type):
        return await self._execute(self._f(self.op_get_permissions, *conditions, group_id=group_id, type=type))

    async def set_or_update_permissions(self, group_id=None, type=None, *, ps: list):
        return await self._execute(self._f(self.op_set_or_update_permissions, group_id=group_id, type=type, ps=ps))

    async def query_delete_permissions(self, *conditions, group_id, type):
        return await self._execute(self._f(self.op_query_delete_permissions, *conditions, group_id=group_id, type=type))

    def op_get_users(self, group_id=None, *conditions):
        self.op_only_or_raise(self.TABLE.id == group_id)
        query = self.session.query(table.UserGroupRelation.character,
                                   table.UserGroupRelation.user_id,
                                   table.User.name,
                                   table.User.alias,
                                   table.User.mail). \
            select_from(table.UserGroupRelation). \
            join(table.User, table.User.id == table.UserGroupRelation.user_id). \
            filter(table.UserGroupRelation.group_id == group_id). \
            filter(*conditions)
        return [r._asdict() for r in query.all()]

    def op_add_or_update_users(self, group_id=None, *, users: list):
        group = self.op_only_or_raise(self.TABLE.id == group_id)
        eps = self.op_get_users(group_id=group_id)
        eps_p_dict = {i["user_id"]: i for i in eps}
        for item in users:
            # {character: xxx, user_id: xxx}
            if item["user_id"] not in eps_p_dict:
                new_p = table.UserGroupRelation(group_id=group["id"],
                                                user_id=item["user_id"],
                                                character=item["character"])
                self.session.add(new_p)
            else:
                # item["permission"] already in check character
                if item["character"] != eps_p_dict[item["user_id"]]["character"]:
                    # character update
                    self.session.query(table.UserGroupRelation). \
                        filter(table.UserGroupRelation.group_id == group["id"],
                               table.UserGroupRelation.user_id == item["user_id"]). \
                        update({"character": item["character"]},
                               synchronize_session="fetch")
        self.session.flush()

    def op_query_delete_users(self, *conditions, group_id=None):
        self.session.query(table.UserGroupRelation). \
            select_from(table.UserGroupRelation). \
            join(self.TABLE, self.TABLE.id == table.UserGroupRelation.group_id). \
            filter(self.TABLE.id == group_id). \
            filter(*conditions).delete(synchronize_session="fetch")

    async def get_users(self, *conditions, group_id=None):
        return await self._execute(self._f(self.op_get_users, *conditions, group_id=group_id))

    async def add_or_update_users(self, group_id=None, *, users: list):
        return await self._execute(self._f(self.op_add_or_update_users, group_id=group_id, users=users))

    async def query_delete_users(self, *conditions, group_id=None):
        return await self._execute(self._f(self.op_query_delete_users, *conditions, group_id=group_id))


class WorkFlow(ABCOrm):
    TABLE = table.Workflow


class Host(ABCOrm):
    TABLE = table.Host
    PK = "ip"


class HostFilter(ABCOrm):
    TABLE = table.HostFilter


class Operator(ABCOrm):
    TABLE = table.Operator


class Operation(ABCOrm):
    TABLE = table.Operation


class Task(ABCOrm):
    TABLE = table.Task


class OrmObject(Object, metaclass=abc.ABCMeta):
    __ORM__ = ABCOrm

    @property
    def orm(self):
        return self._orm_instance

    def __init__(self, meta: dict, loop=None, orm_session=None):
        super().__init__(meta, loop=loop)
        self.orm_session = orm_session or DBSession()
        self._orm_instance = self.__ORM__(session=self.orm_session)
