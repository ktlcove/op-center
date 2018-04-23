PROJECT_NAME = "op-center"
DEFAULT_CFG_FILE = "op_center/cfg.json"

USER_TYPE_LOCAL = "local"
USER_TYPE_LDAP = "ldap"
USER_TYPES = [USER_TYPE_LDAP, USER_TYPE_LOCAL]

UG_CHARACTER_OWNER = 100
UG_CHARACTER_MASTER = 80
UG_CHARACTER_DEVELOPER = 60
UG_CHARACTER_REPORTER = 40
UG_CHARACTER_GUEST = 20
UG_CHARACTERS = [UG_CHARACTER_OWNER, UG_CHARACTER_MASTER,
                 UG_CHARACTER_DEVELOPER, UG_CHARACTER_REPORTER,
                 UG_CHARACTER_GUEST]
UG_CHARACTER_VALUE_2_KEY_MAP = {
    UG_CHARACTER_OWNER: "owner",
    UG_CHARACTER_MASTER: "master",
    UG_CHARACTER_DEVELOPER: "developer",
    UG_CHARACTER_REPORTER: "reporter",
    UG_CHARACTER_GUEST: "guest",
}
UG_CHARACTERS_COUNT = len(UG_CHARACTERS)

PMS_CREATE_USER = "create_user"
PMS_DELETE_USER = "delete_user"
PMS_MODIFY_USER = "modify_user"
PMS_SEARCH_USER = "search_user"

PMS_CREATE_OPERATOR = "create_operator"
PMS_DELETE_OPERATOR = "delete_operator"
PMS_MODIFY_OPERATOR = "modify_operator"
PMS_SEARCH_OPERATOR = "search_operator"

PMS_USE_HOST_FILTER = "use_host_filter"
PMS_SEARCH_HOST_FILTER = "search_host_filter"
PMS_CREATE_HOST_FILTER = "create_host_filter"
PMS_MODIFY_HOST_FILTER = "modify_host_filter"
PMS_DELETE_HOST_FILTER = "delete_host_filter"

PMS_USE_WORKFLOW = "use_workflow"
PMS_SEARCH_WORKFLOW = "search_workflow"
PMS_CREATE_WORKFLOW = "create_workflow"
PMS_DELETE_WORKFLOW = "delete_workflow"
PMS_MODIFY_WORKFLOW = "modify_workflow"

PMS_RUN_OPERATION = "run_operation"
PMS_CREATE_OPERATION = "create_operation"
PMS_DELETE_OPERATION = "delete_operation"
PMS_MODIFY_OPERATION = "modify_operation"
PMS_SEARCH_OPERATION = "search_operation"

PMS_SEARCH_TASK = "search_task"
PMS_DELETE_TASK = "delete_task"
PMS_OPERATION_TASK = "operation_task"

PMS_TYPE_OVERALL = "overall"
PMS_TYPE_PRIVATE = "private"

PRIVATE_PMSS = {PMS_USE_HOST_FILTER,
                PMS_SEARCH_HOST_FILTER,
                PMS_CREATE_HOST_FILTER,
                PMS_MODIFY_HOST_FILTER,
                PMS_DELETE_HOST_FILTER,

                PMS_USE_WORKFLOW,
                PMS_SEARCH_WORKFLOW,
                PMS_CREATE_WORKFLOW,
                PMS_DELETE_WORKFLOW,
                PMS_MODIFY_WORKFLOW,

                PMS_RUN_OPERATION,
                PMS_CREATE_OPERATION,
                PMS_DELETE_OPERATION,
                PMS_MODIFY_OPERATION,
                PMS_SEARCH_OPERATION,

                PMS_SEARCH_TASK,
                PMS_DELETE_TASK,
                PMS_OPERATION_TASK,
                }

OVERALL_PMSS = {PMS_CREATE_USER,
                PMS_DELETE_USER,
                PMS_MODIFY_USER,
                PMS_SEARCH_USER,
                PMS_CREATE_OPERATOR,
                PMS_DELETE_OPERATOR,
                PMS_MODIFY_OPERATOR,
                PMS_SEARCH_OPERATOR,
                *PRIVATE_PMSS
                }

HOST_TYPE_VIRTUAL = "virtual"
HOST_TYPE_PHYSICAL = "physical"
HOST_TYPES = [HOST_TYPE_PHYSICAL, HOST_TYPE_VIRTUAL]

WORKFLOW_TYPE_REMOTE = "remote"
WORKFLOW_TYPE_SERVER = "server"
WORKFLOW_TYPES = [WORKFLOW_TYPE_REMOTE, WORKFLOW_TYPE_SERVER]

OPERATOR_TYPE_CELERY_REDIS = "celery-redis"
OPERATOR_TYPE_COOLY = "cooly"
OPERATOR_TYPES = [OPERATOR_TYPE_CELERY_REDIS, OPERATOR_TYPE_COOLY]

CELERY_TASK_NAME = "celery-task"

TASK_STATUS_WAIT = "wait"
TASK_STATUS_QUEUE = "queue"
TASK_STATUS_ROUTER = "router"
TASK_STATUS_NOT_BEGIN = "not_begin" # not_begin = wait/queue/router
TASK_STATUS_RUNNING = "running"
TASK_STATUS_FINISH = "finish"
TASK_STATUS_SUCCESS = "success"
TASK_STATUS_FAILURE = "failure"

TASK_ALL_STATUS = [TASK_STATUS_WAIT,
                   TASK_STATUS_QUEUE,
                   TASK_STATUS_ROUTER,
                   TASK_STATUS_RUNNING,
                   TASK_STATUS_FINISH,
                   TASK_STATUS_SUCCESS,
                   TASK_STATUS_FAILURE]

HOST_ENV_PREFIX = "ARGS_"

TASK_RETURN_CODE_CONNECTION_ERROR = -1000
TASK_RETURN_CODE_SSH_TIMEOUT = -2000
TASK_RETURN_CODE_SSH_CMD_TIMEOUT = -2101
TASK_RETURN_CODE_SFTP_TRANSFER_TIMEOUT = -2201
TASK_RETURN_CODE_SFTP_TRANSFER_IO_ERROR = -2202
TASK_RETURN_CODE_UNKNOWN_ERROR = -3000
TASK_RETURN_CODE_SYSTEM_ERROR = -5000
TASK_RETURN_CODE_UNKNOWN = -9999
