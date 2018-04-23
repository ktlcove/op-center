import functools

import aiohttp

from op_center.basic import cfg
from op_center.other_system import ABCSystem


class ISSystemResponseException(Exception):
    pass


class ISSystemCache(dict):
    pass


def issystem_cache(f):
    @functools.wraps(f)
    async def real_func(self, *args, **kwargs):
        if kwargs:
            raise RuntimeError()
        key = hash(f.__name__ + "|" + "|".join(args))
        if key not in self._cache_data:
            result = await f(self, *args, **kwargs)
            self._cache_data[key] = result
        return self._cache_data[key]

    return real_func


class ISSystem(ABCSystem):
    AUTH_HEADERS = {
        "X-Auth-Token": cfg["other_system"]["issystem"]["token"],
        "Content-Type": "application/json",
    }
    SITE = cfg["other_system"]["issystem"]["site"]
    TIMEOUT = cfg["other_system"]["issystem"]["timeout"]

    def __init__(self):
        super().__init__()
        self._cache_data = ISSystemCache()

    @property
    def session(self):
        if not self._session:
            self._session = aiohttp.ClientSession(
                headers=self.AUTH_HEADERS)
        return self._session

    async def _parse_response(self, response):
        return response

    @issystem_cache
    async def get_ip_basic_info(self, ip):
        apps_submodules = await self.get_ip_apps(ip)
        if not apps_submodules:
            return {}
        else:
            result = {"enabled": [], "zone": None, "app_name": [], "app2": [], "app3": [], "app4": []}
            done = []
            for app_submodule in apps_submodules:
                app = app_submodule["app_name"]
                if app not in result["app_name"]:
                    result["app_name"].append(app)
                submodule = app_submodule["submodule_name"]
                app_detail = await self.get_app_detail(app)
                department = app_detail["department"]
                appid = app_detail["third_name"]
                if appid not in result["app3"]:
                    result["app3"].append(appid)
                app4 = appid + "." + submodule
                app2 = app + "." + submodule
                if app2 not in result["app2"]:
                    result["app2"].append(app2)
                if app4 not in result["app4"]:
                    result["app4"].append(app4)

                _meta = {
                    "app_name": app,
                    "app2": app2,
                    "app3": appid,
                    "app4": app4,
                    "department": department,
                }

                if app not in done:
                    hosts = [i for i in await self.get_app_hosts(app) if i["ip"] == ip]
                    for h in hosts:
                        result["enabled"].append({
                            "data": h["enabled"],
                            **_meta,
                        })
                        result["zone"] = h["zone_name"]
                        done.append(app)
                    app_info = await self.get_app_info(app)
                    for key, value in app_info.items():
                        if "app_info_" + key not in result:
                            result["app_info_" + key] = []

                        result["app_info_" + key].append({
                            "data": value,
                            **_meta,
                        })
                if app + "." + submodule not in done:
                    app_submodule_info = await self.get_app_submodule_info(app, submodule)
                    for key, value in app_submodule_info.items():
                        if "app_submodule_info_" + key not in result:
                            result["app_submodule_info_" + key] = []

                        result["app_submodule_info_" + key].append({
                            "data": value,
                            **_meta,
                        })
                    done.append(app + "." + submodule)

            return result

    @issystem_cache
    async def get_app_detail(self, app_name):
        raise NotImplementedError

    @issystem_cache
    async def get_app_hosts(self, app_name):
        raise NotImplementedError

    @issystem_cache
    async def get_ip_apps(self, ip):
        raise NotImplementedError

    @issystem_cache
    async def get_app_info(self, app_name):
        raise NotImplementedError

    @issystem_cache
    async def get_app_submodule_info(self, app_name, submodule_name):
        raise NotImplementedError
