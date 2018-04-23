import logging

from op_center.basic import HOST_ENV_PREFIX
from op_center.crontab import ABCCrontab
from op_center.other_system.cmdb import CMDB
from op_center.other_system.issystem import ISSystem
from op_center.server import orm

logger = logging.getLogger(__name__)


class RefreshAllHost(ABCCrontab):

    def __init__(self):
        self.cmdb = CMDB()
        self.issystem = ISSystem()
        self.host = orm.Host()

    async def run(self):

        created = 0
        updated = 0
        enabled = 0

        print(f"get all host from cmdb ...")
        cmdb_hosts = await self.cmdb.get_hosts()

        print(f"work start set all host state to disable...")
        await self.host.query_update(ok=False)
        total = await self.host.count()
        print(f"work start set all host state to disable -> ok...")
        for basic in cmdb_hosts:
            ip = basic["main_ip"].strip()
            if ip == "127.0.0.1":
                continue
            if type(ip) is not str:
                raise RuntimeError(ip)
            issystem_info = await self.issystem.get_ip_basic_info(ip)
            h = await self.host.only_or_none(orm.t.h.ip == ip)
            if h:
                # if await self.host.query(orm.t.h.ip == ip, orm.t.h.ok == True):
                #     print(ip)
                #     break
                await self.host.query_update(orm.t.h.ip == ip,
                                             basic=basic,
                                             issystem=issystem_info,
                                             envs={HOST_ENV_PREFIX + "IDC": basic["idc"],
                                                   HOST_ENV_PREFIX + "ENV": basic["env_type"],
                                                   HOST_ENV_PREFIX + "IP": ip,
                                                   HOST_ENV_PREFIX + "APP4": " ".join(issystem_info.get("app4", [])),
                                                   HOST_ENV_PREFIX + "ZONE": issystem_info.get("zone", ""),
                                                   HOST_ENV_PREFIX + "APP_NAME": " ".join(
                                                       issystem_info.get("app_name", []))},
                                             ok=True)
                updated += 1
                print(f"host `{ip}` updated ...")
            else:
                await self.host.create(ip=ip,
                                       basic=basic,
                                       issystem=issystem_info,
                                       envs={HOST_ENV_PREFIX + "IDC": basic["idc"],
                                             HOST_ENV_PREFIX + "ENV": basic["env_type"],
                                             HOST_ENV_PREFIX + "IP": ip,
                                             HOST_ENV_PREFIX + "APP4": " ".join(issystem_info.get("app4", [])),
                                             HOST_ENV_PREFIX + "ZONE": issystem_info.get("zone", ""),
                                             HOST_ENV_PREFIX + "APP_NAME": " ".join(issystem_info.get("app_name", []))},
                                       ok=True)
                created += 1
                print(f"host `{ip}` created ...")
            enabled += 1

        print(f"""create: {created}\t update: {updated}\t total: {total}\t enable: {enabled}""")


if __name__ == '__main__':
    refresher = RefreshAllHost()
    refresher()
