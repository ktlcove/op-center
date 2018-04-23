from op_center.server.http.views import ABCOpCenterView


class Operator(ABCOpCenterView):

    async def post(self):
        meta = await self.controller.create_operator(
            name=self.request.POST.get("name", required=True),
            description=self.request.POST.get("description"),
            type=self.request.POST.get("type", required=True),
            mq_link=self.request.POST.get("mq_link", required=True))
        return await self.response(data=meta)

    async def get(self):
        data = await self.controller.get_operator()
        return await self.response(data=data)


class OperatorDetail(ABCOpCenterView):

    async def post(self):
        await self.controller.update_operator(
            id=int(self.url_args.get("id", required=True)),
            name=self.request.POST.get("name"),
            description=self.request.POST.get("description"),
            mq_link=self.request.POST.get("mq_link"))
        return await self.response()

    async def get(self):
        result = await self.controller.get_operator(id=int(self.url_args.get("id", required=True)))
        if result:
            return await self.response(data=result[0])
        else:
            return await self.response(code=404, error="target not found")

    async def delete(self):
        await self.controller.delete_operator(id=int(self.url_args.get("id", required=True)))
        return await self.response()
