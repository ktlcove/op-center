import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

from op_center.basic import USER_TYPE_LDAP, WORKFLOW_TYPE_SERVER

meta = declarative_base()


class ABCTable(meta):
    __abstract__ = True

    def _asdict(self):
        return {k: v for k, v in self._sa_instance_state.dict.items()
                if k != "_sa_instance_state"}


class User(ABCTable):
    __tablename__ = "user"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True)
    alias = sa.Column("alias", sa.String(50), nullable=False, index=True)
    mail = sa.Column("mail", sa.String(150), nullable=False, index=True)
    type = sa.Column("type", sa.String(20), nullable=False, index=True, default=USER_TYPE_LDAP)
    token = sa.Column("token", sa.String(120), nullable=False, index=True)
    password = sa.Column("password", sa.String(120), nullable=True, index=False)
    basic_group_id = sa.Column("basic_group_id", sa.ForeignKey("group.id"), nullable=False, index=True)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate=sa.text("NOW()"))


class Group(ABCTable):
    __tablename__ = "group"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True, primary_key=True)
    description = sa.Column("description", sa.Text(), nullable=True)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()", index=True)
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class UserGroupRelation(ABCTable):
    __tablename__ = "user_group_relation"
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), primary_key=True)
    user_id = sa.Column('user_id', sa.ForeignKey('user.id'), primary_key=True)
    character = sa.Column("character", sa.String(50), nullable=False, index=True)


class GroupPermission(ABCTable):
    __tablename__ = "group_permission"
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), primary_key=True)
    type = sa.Column("type", sa.String(20), primary_key=True)
    permission = sa.Column("permission", sa.String(100), primary_key=True)
    character = sa.Column("character", sa.String(100), nullable=False, index=True)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class Workflow(ABCTable):
    __tablename__ = "workflow"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True)
    description = sa.Column("description", sa.Text(), nullable=True)
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), nullable=True, index=True)
    type = sa.Column("type", sa.String(20), nullable=False, index=True, default=WORKFLOW_TYPE_SERVER)
    steps = sa.Column("steps", sa.JSON, nullable=False)
    basic = sa.Column("basic", sa.JSON, nullable=False)
    envs = sa.Column("envs", sa.JSON, nullable=False)
    args = sa.Column("args", sa.JSON, nullable=False)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class Host(ABCTable):
    __tablename__ = "host"
    ip = sa.Column("ip", sa.String(20), primary_key=True)
    basic = sa.Column("basic", sa.JSON, nullable=False, index=True)
    issystem = sa.Column("issystem", sa.JSON, nullable=True, index=True)
    envs = sa.Column("envs", sa.JSON, nullable=False, index=True)
    ok = sa.Column("ok", sa.Boolean, nullable=False, index=True, default=False)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class HostFilter(ABCTable):
    __tablename__ = "host_filter"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True)
    description = sa.Column("description", sa.Text(), nullable=True)
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), nullable=True, index=True)
    filters = sa.Column("filters", sa.JSON, nullable=False)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class Operator(ABCTable):
    __tablename__ = "operator"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True)
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), nullable=True, index=True)
    description = sa.Column("description", sa.Text(), nullable=True)
    type = sa.Column("type", sa.String(20), nullable=False, index=True)
    mq_link = sa.Column("mq_link", sa.JSON, nullable=False, index=True)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class Operation(ABCTable):
    __tablename__ = "operation"
    id = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column("name", sa.String(50), nullable=False, unique=True)
    description = sa.Column("description", sa.Text(), nullable=True)
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), nullable=True, index=True)
    workflow_id = sa.Column("workflow_id", sa.ForeignKey("workflow.id"), nullable=False, index=True)
    host_filter_id = sa.Column("host_filter_id", sa.ForeignKey("host_filter.id"), nullable=False, index=True)
    operator_id = sa.Column("operator_id", sa.ForeignKey("operator.id"), nullable=True, index=True)
    cache = sa.Column("cache", sa.JSON, nullable=False, index=False)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")


class Task(ABCTable):
    __tablename__ = "task"
    id = sa.Column("id", sa.String(50), primary_key=True)
    operation_id = sa.Column("operation_id", sa.ForeignKey("operation.id"), nullable=False, index=True)
    group_id = sa.Column("group_id", sa.ForeignKey("group.id"), nullable=True, index=True)
    hosts = sa.Column("hosts", sa.JSON, nullable=True, index=True)
    workflow = sa.Column("workflow", sa.JSON, nullable=False, index=True)
    operator_id = sa.Column("operator_id", sa.ForeignKey("operator.id"), nullable=True, index=True)
    running_kwargs = sa.Column("running_kwargs", sa.JSON, nullable=True, index=True)
    runner = sa.Column("runner", sa.String(50), nullable=False, index=True)
    status = sa.Column("status", sa.JSON, nullable=False, index=True)
    result = sa.Column("result", sa.JSON, nullable=False, index=True)
    c_time = sa.Column("c_time", sa.DateTime, server_default="NOW()")
    m_time = sa.Column("m_time", sa.DateTime, server_default="NOW()", server_onupdate="NOW()")
    f_time = sa.Column("f_time", sa.DateTime, nullable=True, index=True)
