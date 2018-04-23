from op_center.basic import USER_TYPE_LOCAL, USER_TYPE_LDAP, UG_CHARACTER_OWNER, UG_CHARACTER_MASTER, OVERALL_PMSS, \
    PMS_TYPE_OVERALL, PMS_TYPE_PRIVATE, PRIVATE_PMSS, PMS_SEARCH_USER, PMS_SEARCH_OPERATOR, PMS_SEARCH_HOST_FILTER, \
    PMS_SEARCH_WORKFLOW, PMS_SEARCH_OPERATION, UG_CHARACTER_REPORTER, UG_CHARACTER_GUEST
from op_center.bin import run
from op_center.server import orm


class DBInitialize:

    def __init__(self):
        self.user = orm.User()
        self.group = orm.Group()

    async def ensure_group(self):
        # admin
        if not await self.group.only_or_none(orm.t.g.name == "admins"):
            await self.group.create(id=1, name="admins", description="admins default group")
        print(await self.group.only_or_none(orm.t.g.name == "admins"))
        await self.group.set_or_update_permissions(group_id=1, type=PMS_TYPE_OVERALL,
                                                   ps=[{"character": UG_CHARACTER_MASTER, "permission": pms}
                                                       for pms in OVERALL_PMSS])

        await self.group.set_or_update_permissions(group_id=1, type=PMS_TYPE_PRIVATE,
                                                   ps=[{"character": UG_CHARACTER_MASTER, "permission": pms}
                                                       for pms in PRIVATE_PMSS])

        # anonymous
        if not await self.group.only_or_none(orm.t.g.name == "anonymous"):
            await self.group.create(id=2, name="anonymous", description="anonymous default group")
        print(await self.group.only_or_none(orm.t.g.name == "anonymous"))

        # public
        if not await self.group.only_or_none(orm.t.g.name == "public"):
            await self.group.create(id=3, name="public", description="public group every user default in this")
        print(await self.group.only_or_none(orm.t.g.name == "public"))
        public_group_pms = {
            PMS_SEARCH_USER,
            PMS_SEARCH_OPERATOR,
            PMS_SEARCH_HOST_FILTER,
            PMS_SEARCH_WORKFLOW,
            PMS_SEARCH_OPERATION,
        }

        await self.group.set_or_update_permissions(group_id=3, type=PMS_TYPE_PRIVATE,
                                                   ps=[{"character": UG_CHARACTER_REPORTER, "permission": pms}
                                                       for pms in public_group_pms])

    async def ensure_user(self):
        #
        # local-admin
        admins = await self.group.only_or_raise(orm.t.g.name == "admins")
        anonymous = await self.group.only_or_raise(orm.t.g.name == "anonymous")

        local_admin = await self.user.only_or_none(orm.t.u.name == "local-admin")
        if not local_admin:
            user_id = await self.user.create(id=1,
                                             name="local-admin",
                                             alias="系统管理员",
                                             mail="root@localhost",
                                             type=USER_TYPE_LOCAL,
                                             password="admin",
                                             basic_group_character=UG_CHARACTER_OWNER,
                                             basic_group_id=admins["id"])
            print(user_id)
            await self.user.join_group(user_id=user_id, group_id=3, character=UG_CHARACTER_OWNER)

        guest = await self.user.only_or_none(orm.t.u.name == "anonymous")
        if not guest:
            user_id = await self.user.create(id=2,
                                             name="anonymous",
                                             alias="匿名用户",
                                             mail="anonymous@localhost",
                                             type=USER_TYPE_LOCAL,
                                             password=None,
                                             basic_group_character=UG_CHARACTER_OWNER,
                                             basic_group_id=anonymous["id"])
            print(user_id)
            await self.user.join_group(user_id=user_id, group_id=3, character=UG_CHARACTER_GUEST)

        for name in ["local-admin", "anonymous"]:
            print(await self.user.only_or_raise(orm.t.u.name == name))


if __name__ == '__main__':
    d = DBInitialize()
    run(d.ensure_group())
    run(d.ensure_user())
