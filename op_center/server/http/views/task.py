from op_center.server.http.views import ABCOpCenterView


class Task(ABCOpCenterView):

    async def get(self):
        data = await self.controller.get_task()
        return await self.response(data=data)


class TaskDetail(ABCOpCenterView):

    async def get(self):
        result = await self.controller.get_task(id=str(self.url_args.get("id", required=True)))
        if result:
            return await self.response(data=result[0])
        else:
            return await self.response(code=404, error="target not found")

    # async def delete(self):
    #     await self.controller.delete_task(id=int(self.url_args.get("id", required=True)))
    #     return await self.response()


class TaskStatus(ABCOpCenterView):

    async def get(self):
        return await self.response(
            data=await self.controller.get_task_status(id=self.url_args.get("id", required=True))
        )


class TaskRedo(ABCOpCenterView):

    async def post(self):
        return await self.response(
            data=await self.controller.redo_task(id=str(self.url_args.get("id", required=True)),
                                                 target_hosts_filter=self.request.POST.get("target_host_filter",
                                                                                           default={}))
        )


class TaskResult(ABCOpCenterView):

    async def get(self):
        return await self.response(
            data=await self.controller.get_task_result(id=str(self.url_args.get("id", required=True)))
        )


class TaskCodeMap(ABCOpCenterView):

    async def get(self):
        return await self.response(
            data=await self.controller.task_code_map(id=str(self.url_args.get("id", required=True)))
        )


class TaskResultParse(ABCOpCenterView):

    async def post(self):
        return await self.response(
            data=await self.controller.parse_task_result(id=str(self.url_args.get("id", required=True)),
                                                         **self.request.POST)
        )


class TaskResultParseSimpleMode(ABCOpCenterView):

    async def post(self):
        data = await self.controller.parse_task_result(id=str(self.url_args.get("id", required=True)),
                                                       **self.request.POST)
        real_data = data["details"]
        result = {ip: [d["code"], d["stderr"], d["stdout"]] for ip, d in real_data.items()}
        return await self.response(data=result)
