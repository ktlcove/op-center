from op_center.basic import UG_CHARACTER_VALUE_2_KEY_MAP
from op_center.server import user
from op_center.server.controller import controller
from op_center.server.http.views import ABCOpCenterView


class Auth(ABCOpCenterView):

    async def initialize(self):
        self.controller = controller.Controller(self.user)

    async def post(self):
        username = self.request.POST.get("username", required=True)
        password = self.request.POST.get("password", required=True)
        self.user = await user.User.login_by_password(username, password)
        self.session["name"] = self.user.name
        return await self.response()


class MyInfo(ABCOpCenterView):

    async def get(self):
        data = {
            "meta": self.user.meta,
            "groups": await self.user.my_groups(),
            "basic_group": await self.user.my_basic_group(),
            "overall_permissions": await self.user.my_overall_permissions()
        }
        for g in data["groups"]:
            g["character"] = UG_CHARACTER_VALUE_2_KEY_MAP[g["character"]]
        data["basic_group"]["character"] = UG_CHARACTER_VALUE_2_KEY_MAP[data["basic_group"]["character"]]

        return await self.response(data=data)
