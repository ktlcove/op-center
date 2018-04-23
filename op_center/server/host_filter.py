import abc
import json
import logging

from sqlalchemy import and_, or_
from sqlalchemy.sql import func

from op_center.server import orm, ServerException

logger = logging.getLogger(__name__)

ALL_HOST_ITEM_FILTERS = {
    # name -> host_item_filter
}


class HostFilterException(ServerException):
    pass


class HostFilterItemException(HostFilterException):
    pass


class HostFilterItemArgsTypeWrong(HostFilterItemException):
    code = 400


class HostFilterItemConditionNotAllow(HostFilterItemException):
    code = 400


class HostItemFilterNotFound(HostFilterItemException):
    pass


class ABCHostItemFilter(metaclass=abc.ABCMeta):
    NAME = None
    key = None

    ENABLED_CONDITIONS = ["in", "not_in", "is", "is_not"]

    def __init__(self, kwargs):
        self.kwargs = kwargs
        logger.debug(kwargs)
        self.result = {}

    def query_condition(self) -> dict:
        for condition, args in self.kwargs.items():
            if condition not in self.ENABLED_CONDITIONS:
                raise HostFilterItemConditionNotAllow(f"condition {condition} not allow in {self.NAME}")
            if hasattr(self, f"op_{condition}"):
                attribute = getattr(self, f"op_{condition}")
                # logger.debug(f"{condition}, {args}, {self.key}")
                r = attribute(args)
                logger.debug(r)
                self.result[f"{self.NAME}_{condition}"] = r
        logger.debug(self.result)
        return self.result

    def op_in(self, args):
        if type(args) is not list and type(args) is not tuple and type(args) is not set:
            raise HostFilterItemArgsTypeWrong("args type must be an iterable[list,tuple,set]"
                                              f" not {repr(args)}")
        return self.key.in_(args)

    def op_not_in(self, args):
        if type(args) is not list and type(args) is not tuple and type(args) is not set:
            raise HostFilterItemArgsTypeWrong("args type must be an iterable[list,tuple,set]")
        return self.key.notin_(args)

    def op_is(self, args):
        return self.key == args

    def op_is_not(self, args):
        return self.key != args


def host_item_filter_register(cls: ABCHostItemFilter):
    if cls.NAME not in ALL_HOST_ITEM_FILTERS:
        ALL_HOST_ITEM_FILTERS[cls.NAME] = cls
    else:
        raise RuntimeError(f"host_item_filter {cls.NAME} "
                           f"already in ALL_HOST_ITEM_FILTERS")
    return cls


@host_item_filter_register
class HostItemInISSystemFilter(ABCHostItemFilter):
    NAME = "in_issystem"
    key = orm.t.h.issystem.expression
    ENABLED_CONDITIONS = ["is", "is_not"]

    def op_is(self, args):
        if args:
            return func.json_length(self.key) > 0
        else:
            return func.json_length(self.key) == 0

    def op_is_not(self, args):
        return self.op_is(not args)


@host_item_filter_register
class HostItemISSystemEnableFilter(ABCHostItemFilter):
    NAME = "issystem_enabled"
    key = orm.t.h.issystem.expression["enabled"]
    ENABLED_CONDITIONS = ["only_has", "has", "multi_state"]

    def op_has(self, args):
        # if args:
        #     return func.json_contains(self.key, {"data": args}, "$.enabled")
        # else:
        #     return func.json_contains(self.key, {"data": args}, "$.enabled")
        return func.json_contains(self.key, json.dumps({"data": args}))

    def op_only_has(self, args):
        return func.json_contains(self.key, json.dumps({"data": args})) and \
               not func.json_contains(self.key, json.dumps({"data": not args}))

    def op_multi_state(self, args):
        if args:
            return (json.dumps({"data": True}) in self.key) and \
                   (json.dumps({"data": False}) in self.key)
        else:
            return True


@host_item_filter_register
class HostItemIDCFilter(ABCHostItemFilter):
    NAME = "idc"
    key = orm.t.h.basic.expression["idc"]


@host_item_filter_register
class HostItemOKFilter(ABCHostItemFilter):
    NAME = "ok"
    key = orm.t.h.ok.expression


@host_item_filter_register
class HostItemIpFilter(ABCHostItemFilter):
    NAME = "ip"
    ENABLED_CONDITIONS = ["in", "not_in", "is", "is_not", "regexp"]
    key = orm.t.h.ip.expression

    def op_regexp(self, args):
        if type(args) is not str:
            raise HostFilterItemArgsTypeWrong(f"regexp condition args must be a string pattern")
        return self.key.op("regexp")(args)


@host_item_filter_register
class HostItemTypeFilter(ABCHostItemFilter):
    NAME = "type"
    key = orm.t.h.basic.expression["machine_type"]


@host_item_filter_register
class HostItemEnvFilter(ABCHostItemFilter):
    NAME = 'env'
    key = orm.t.h.basic.expression["env_type"]


@host_item_filter_register
class HostItemAppnameFilter(ABCHostItemFilter):
    NAME = "appname"
    key = orm.t.h.issystem.expression["appname"]


@host_item_filter_register
class HostItemApp4Filter(ABCHostItemFilter):
    NAME = "app4"
    key = orm.t.h.issystem.expression["app4"]


@host_item_filter_register
class HostItemDepartmentFilter(ABCHostItemFilter):
    NAME = "department"
    key = orm.t.h.issystem["department"]


@host_item_filter_register
class HostItemZoneFilter(ABCHostItemFilter):
    NAME = "zone"
    key = orm.t.h.issystem["zone"]


class HostFilter(orm.OrmObject):
    __ORM__ = orm.HostFilter
    __HOST_ORM__ = orm.Host

    """
    filter:
    - idc:
          in:
          - idc1
          - idc2
    - department:
          is: dep

    - app_name:
          in:
          - {app}

    - ip:
        regexp: xxx            
    """

    DEFAULT_CONDITIONS = {
        "machine_type_in": or_(orm.t.h.basic.expression["machine_type"] == "phy",
                               orm.t.h.basic.expression["machine_type"] == "vmhost",
                               orm.t.h.basic.expression["machine_type"] == "vm"),
        "ok_is": orm.t.h.ok,
    }

    @classmethod
    async def create_by_name_or_id(cls, name=None, id=None, loop=None, orm_session=None):
        orm_instance = orm_session or cls.__ORM__()
        if name:
            obj = await orm_instance.only_or_raise(orm.t.hf.name == name)
        else:
            obj = await orm_instance.only_or_raise(orm.t.hf.id == id)
        return cls(obj, loop=loop, orm_session=orm_session)

    def __init__(self, meta, loop=None, orm_session=None):
        super().__init__(meta, loop=loop, orm_session=orm_session)
        self._host_orm_instance = self.__HOST_ORM__(session=self.orm_session)
        self._filters = []

    @property
    def filters(self):
        if not self._filters:
            logger.debug(self.meta["filters"])
            for _filter in self.meta['filters']:
                logger.debug(_filter)
                for f_name, f_args in _filter.items():
                    _ItemFilter = ALL_HOST_ITEM_FILTERS.get(f_name, None)
                    logger.debug(_ItemFilter)
                    if not _ItemFilter:
                        raise HostItemFilterNotFound(f"host item `{f_name}` not found")
                    self._filters.append(_ItemFilter(f_args))
        return self._filters

    def get_query_condition(self):
        conditions = {**self.DEFAULT_CONDITIONS}
        for _filter in self.filters:
            conditions.update(_filter.query_condition())
        logger.debug(conditions)
        return conditions

    async def get_hosts(self, columns=None):
        """result is a Host list"""
        conditions = self.get_query_condition()
        return await self._host_orm_instance.query(*conditions.values(), columns=columns)
