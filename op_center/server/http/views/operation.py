from op_center.server.http.views import ABCOpCenterView


class Operation(ABCOpCenterView):

    async def post(self):
        meta = await self.controller.create_operation(
            name=self.request.POST.get("name", required=True),
            description=self.request.POST.get("description"),
            workflow_id=self.request.POST.get("workflow_id"),
            operator_id=self.request.POST.get("operator_id"),
            host_filter_id=self.request.POST.get("host_filter_id"),
            group_id=self.request.POST.get("group_id"),
            auto_fork=self.request.POST.get("auto_fork", default=True, required=True))
        return await self.response(data=meta)

    async def get(self):
        data = await self.controller.get_operation()
        return await self.response(data=data)


class OperationDetail(ABCOpCenterView):

    async def post(self):
        await self.controller.update_operation(
            id=int(self.url_args.get("id", required=True)),
            name=self.request.POST.get("name"),
            description=self.request.POST.get("description"),
            workflow_id=self.request.POST.get("workflow_id"),
            operator_id=self.request.POST.get("operator_id"),
            host_filter_id=self.request.POST.get("host_filter_id"),
            auto_fork=self.request.POST.get("auto_fork", defalut=False))
        return await self.response()

    async def get(self):
        result = await self.controller.get_operation(id=int(self.url_args.get("id", required=True)))
        if result:
            return await self.response(data=result[0])
        else:
            return await self.response(code=404, error="target not found")

    async def delete(self):
        await self.controller.delete_operation(id=int(self.url_args.get("id", required=True)))
        return await self.response()


class OperationRefreshCache(ABCOpCenterView):
    async def post(self):
        await self.controller.operation_refresh_cache(id=int(self.url_args.get("id", required=True)))
        return await self.response()


class OperationRun(ABCOpCenterView):
    async def post(self):
        result = await self.controller.operation_run(
            id=int(self.url_args.get("id", required=True)),
            running_kwargs=self.request.POST.get("running_kwargs"),
            use_cache=self.request.POST.get("use_cache", default=True, required=True),
        )
        return await self.response(data=result)


class OperationFork(ABCOpCenterView):
    pass
