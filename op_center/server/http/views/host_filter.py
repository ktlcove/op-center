from op_center.server.http.views import ABCOpCenterView


class HostFilter(ABCOpCenterView):

    async def post(self):
        meta = await self.controller.create_host_filter(
            name=self.request.POST.get("name", required=True),
            description=self.request.POST.get("description"),
            filters=self.request.POST.get("filters", required=True),
            group_id=self.request.POST.get("group_id"))
        return await self.response(data=meta)

    async def get(self):
        data = await self.controller.get_host_filters()
        return await self.response(data=data)


class HostFilterDetail(ABCOpCenterView):

    async def post(self):
        await self.controller.update_host_filter(
            id=int(self.url_args.get("id", required=True)),
            name=self.request.POST.get("name", required=True),
            description=self.request.POST.get("description"),
            filters=self.request.POST.get("filters", required=True))
        return await self.response()

    async def get(self):
        result = await self.controller.get_host_filters(id=int(self.url_args.get("id", required=True)))
        if result:
            return await self.response(data=result[0])
        else:
            return await self.response(code=404, error="target not found")

    async def delete(self):
        await self.controller.delete_host_filter(id=int(self.url_args.get("id", required=True)))
        return await self.response()


class HostFilterFork(ABCOpCenterView):
    async def post(self):
        data = await self.controller.fork_host_filter(id=int(self.url_args.get("id", required=True)))
        return await self.response(data=data)


class HostFilterHost(ABCOpCenterView):
    async def get(self):
        data = await self.controller.get_host_filter_hosts(id=int(self.url_args.get("id", required=True)))
        return await self.response(data=data)
