import functools
import inspect
import logging

from op_center.basic import get_real_function
from op_center.server.controller.exception import ControllerException

logger = logging.getLogger(__name__)


class PermissionDeny(ControllerException):
    code = 403


class PermissionCheckArgsError(ControllerException):
    code = 500


def overall_pms_required(pms):
    def wrapper(func):
        @functools.wraps(func)
        async def real_func(self, *args, **kwargs):
            if pms in await self.user.my_overall_permissions():
                return await func(self, *args, **kwargs)
            else:
                raise PermissionDeny(f"you have no permission: {pms}")

        return real_func

    return wrapper


def private_pms_required(pms, group_id="group_id", group_id_function=None, group_id_params=None):
    """
    :param pms: string  permission
    :param group_id:  group_id key in call_args
    :param group_id_function: an awaitable function return a real group_id to check private permission
    :param group_id_params: group_id_function's args dict
                            map is:
                            call_args_key_name  ->  group_id_function_key_name
    """
    group_id_params = group_id_params or {}

    def wrapper(func):
        _real_function = get_real_function(func)

        @functools.wraps(func)
        async def real_func_string(self, *args, **kwargs):
            call_args = inspect.getcallargs(_real_function, self, *args, **kwargs)
            try:
                logger.debug(f" call args is : {call_args}")
                gid = call_args[group_id]
            except KeyError:
                raise PermissionCheckArgsError(f"args list not found {group_id}")
            if pms in await self.user.my_group_private_permissions(group_id=gid):
                return await func(self, *args, **kwargs)
            else:
                raise PermissionDeny(f"you have no permission: {pms} in group(id={gid})")

        @functools.wraps(func)
        async def real_func_awaitable(self, *args, **kwargs):
            call_args = inspect.getcallargs(_real_function, self, *args, **kwargs)
            gid = await group_id_function(self, **{call_key: call_args[call_key]
                                                   for f_key, call_key in group_id_params.items()})
            logger.debug(f"get gid result is : {gid}")
            if pms in await self.user.my_group_private_permissions(group_id=gid):
                return await func(self, *args, **kwargs)
            else:
                raise PermissionDeny(f"you have no permission: {pms} in group(id={gid})")

        if group_id_function:
            return real_func_awaitable
        else:
            return real_func_string

    return wrapper


def private_or_overall_pms_required(pms, group_id="group_id", group_id_function=None, group_id_params=None):
    def wrapper(func):
        @functools.wraps(func)
        async def real_func(self, *args, **kwargs):
            try:
                return await private_pms_required(pms,
                                                  group_id=group_id,
                                                  group_id_function=group_id_function,
                                                  group_id_params=group_id_params)(func)(self, *args, **kwargs)
            except PermissionDeny:
                return await overall_pms_required(pms)(func)(self, *args, **kwargs)

        return real_func

    return wrapper


pms_required = private_or_overall_pms_required
