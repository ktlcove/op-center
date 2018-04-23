import concurrent.futures
import logging

import ldap3

from op_center.basic import cfg
from op_center.server import Object
from op_center.server import ServerException

logger = logging.getLogger(__name__)


class LdapException(ServerException):
    pass


class LDAPAdminBindFailedException(LdapException):
    pass


class LoginFailed(LdapException):
    pass


class LDAPBindFailedException(LdapException):
    pass


class LDAPSearchNotFoundException(LdapException):
    pass


class AuthLDAPUtils(Object):
    __LDAP_ECECUTOR__ = concurrent.futures.ThreadPoolExecutor(max_workers=3,
                                                              thread_name_prefix="ldap-exexctor")

    def __init__(self, meta: dict, loop=None):
        super().__init__(meta, loop=loop)
        self.server = ldap3.Server(self.meta["ip"], port=self.meta["port"],
                                   connect_timeout=self.meta["connect_timeout"])
        self._link = None

    async def get_link(self):
        if not self._link:
            self._link = ldap3.Connection(self.server,
                                          user=self.meta["user"],
                                          password=self.meta["password"],
                                          receive_timeout=self.meta["receive_timeout"],
                                          client_strategy=ldap3.REUSABLE,
                                          pool_name="ldap_admin_pool",
                                          pool_size=self.meta["pool_size"],
                                          pool_lifetime=self.meta["pool_lifetime"])
            r = self._link.bind()
            if not r:
                raise LDAPAdminBindFailedException("create admin bind failure")
        return self._link

    async def get_user_info(self, username, **kwargs):

        link = await self.get_link()

        def _search():
            r_id = link.search(self.meta["base_dn"],
                               "(&(sAMAccountName={})(objectclass=person))".format(username),
                               **kwargs)
            response, result = link.get_response(r_id)
            return_value = True if result['type'] == 'searchResDone' and len(response) > 0 else False
            if not return_value:
                raise LDAPSearchNotFoundException("user {} not found in LDAP".format(username))
            logger.debug("search user info in ldap ok , user is {}".format(username))
            entries = link._get_entries(response)
            if len(entries) == 1:
                return entries[0]
            else:
                raise LDAPSearchNotFoundException("user {} not found in LDAP".format(username))

        return await self.loop.run_in_executor(self.__LDAP_ECECUTOR__, _search)

    async def get_user_entry_dn(self, username):
        user_info = await self.get_user_info(username, attributes=ldap3.ALL_ATTRIBUTES)
        if user_info:
            logger.debug(user_info.entry_dn)
            return user_info.entry_dn
        else:
            logger.debug("user {} search ldap failure".format(username))
            return None

    async def auth(self, username, password, user_dn=None):
        if not user_dn:
            try:
                user_dn = await self.get_user_entry_dn(username)
            except LDAPSearchNotFoundException:
                raise LDAPBindFailedException("user entry dn not found")
        if not user_dn:
            raise LDAPBindFailedException("user entry dn not available")

        def _bind():
            user_link = ldap3.Connection(self.server, user=user_dn, password=password, receive_timeout=5000)
            with user_link:
                return user_link.bind()

        if await self.loop.run_in_executor(self.__LDAP_ECECUTOR__, _bind):
            return True
        else:
            raise LDAPBindFailedException("password error")


ldap = AuthLDAPUtils(cfg["ldap"])
