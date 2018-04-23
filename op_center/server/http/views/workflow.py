from op_center.basic import WORKFLOW_TYPE_REMOTE
from op_center.server.http.views import ABCOpCenterView


class Workflow(ABCOpCenterView):

    async def post(self):
        meta = await self.controller.create_workflow(
            name=self.request.POST.get("name", required=True),
            description=self.request.POST.get("description"),
            steps=self.request.POST.get("steps"),
            basic=self.request.POST.get("basic"),
            envs=self.request.POST.get("envs"),
            args=self.request.POST.get("args"),
            type=self.request.POST.get("type", default=WORKFLOW_TYPE_REMOTE),
            group_id=self.request.POST.get("group_id"))
        return await self.response(data=meta)

    async def get(self):
        data = await self.controller.get_workflow()
        return await self.response(data=data)


class WorkflowDetail(ABCOpCenterView):

    async def post(self):
        await self.controller.update_workflow(
            id=int(self.url_args.get("id", required=True)),
            name=self.request.POST.get("name"),
            description=self.request.POST.get("description"),
            steps=self.request.POST.get("steps"),
            basic=self.request.POST.get("basic"),
            envs=self.request.POST.get("envs"),
            args=self.request.POST.get("args"))
        return await self.response()

    async def get(self):
        result = await self.controller.get_workflow(id=int(self.url_args.get("id", required=True)))
        if result:
            return await self.response(data=result[0])
        else:
            return await self.response(code=404, error="target not found")

    async def delete(self):
        await self.controller.delete_workflow(id=int(self.url_args.get("id", required=True)))
        return await self.response()


class WorkflowFork(ABCOpCenterView):
    async def post(self):
        data = await self.controller.fork_workflow(id=int(self.url_args.get("id", required=True)))
        return await self.response(data=data)
