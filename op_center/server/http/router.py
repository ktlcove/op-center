from op_center.server.http.views import host_filter
from op_center.server.http.views import my
from op_center.server.http.views import operation
from op_center.server.http.views import operator
from op_center.server.http.views import task
from op_center.server.http.views import workflow


def setup(app):
    # app.router.add_route("method", "path", "handler_class")
    # 登陆接口
    app.router.add_route("*", "/api/auth/", my.Auth)
    # 单用户专用接口
    app.router.add_route("*", "/api/my/info/", my.MyInfo)
    # 用户
    # app.router.add_route("*", "/api/user/", user.User)
    # 组
    # app.router.add_route("*", "/api/group/", user.Group)
    #
    # host filter
    # get/post
    app.router.add_route("*", "/api/host-filter/", host_filter.HostFilter)
    # get/post/delete
    app.router.add_route("*", "/api/host-filter/{id}/", host_filter.HostFilterDetail)
    # post
    app.router.add_route("*", "/api/host-filter/{id}/fork/", host_filter.HostFilterFork)
    # get
    app.router.add_route("*", "/api/host-filter/{id}/host/", host_filter.HostFilterHost)
    #
    # workflow
    # get/post
    app.router.add_route("*", "/api/workflow/", workflow.Workflow)
    # get/post/delete
    app.router.add_route("*", "/api/workflow/{id}/", workflow.WorkflowDetail)
    # post
    app.router.add_route("*", "/api/workflow/{id}/fork/", workflow.WorkflowFork)
    #
    # operator
    # get/post
    app.router.add_route("*", "/api/operator/", operator.Operator)
    # get/post/delete
    app.router.add_route("*", "/api/operator/{id}/", operator.OperatorDetail)
    #
    # operation
    # get/post
    app.router.add_route("*", "/api/operation/", operation.Operation)
    # get/post/delete
    app.router.add_route("*", "/api/operation/{id}/", operation.OperationDetail)
    # post
    # app.router.add_route("*", "/api/operation/{id}/fork/", operation.OperationFork)
    # post
    app.router.add_route("*", "/api/operation/{id}/refresh-cache/", operation.OperationRefreshCache)
    # post
    app.router.add_route("*", "/api/operation/{id}/run/", operation.OperationRun)
    #
    # task
    # get
    app.router.add_route("*", "/api/task/", task.Task)
    # get/post/delete
    app.router.add_route("*", "/api/task/{id}/", task.TaskDetail)
    # get
    app.router.add_route("*", "/api/task/{id}/status/", task.TaskStatus)
    # get
    app.router.add_route("*", "/api/task/{id}/result/", task.TaskResult)
    # get
    app.router.add_route("*", "/api/task/{id}/code-map/", task.TaskCodeMap)
    # post
    app.router.add_route("*", "/api/task/{id}/result-parse/", task.TaskResultParse)
    # post
    app.router.add_route("*", "/api/task/{id}/result-parse-simple-mode/", task.TaskResultParseSimpleMode)
    # post
    app.router.add_route("*", "/api/task/{id}/redo/", task.TaskRedo)

    # :todo
    # app.router.add_route("*", "/api/task/{id}/archive/", task.TaskArchive)
    # app.router.add_route("*", "/api/task/{id}/kill/", task.TaskArchive)
    # app.router.add_route("*", "/api/task/{id}/clear/", task.TaskArchive)
