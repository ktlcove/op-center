import logging
import unittest

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from op_center.basic import OPERATOR_TYPE_CELERY_REDIS
from op_center.server.http.main import make_app

logger = logging.getLogger(__name__)


class TestHttp(AioHTTPTestCase):

    async def get_application(self):
        return await make_app(loop=self.loop)

    async def setUpAsync(self):
        self.headers = {"Content-Type": "Application/Json"}
        response = await self.client.post("/api/auth/", json={"username": "local-admin", "password": "admin"},
                                          headers=self.headers)

        logger.debug(response.status)
        logger.debug(await response.json())

    @unittest_run_loop
    async def test_my(self):
        response = await self.client.get("/api/my/info/", headers=self.headers)
        logger.debug(response.status)
        logger.debug(await response.json())

    @unittest_run_loop
    async def test_host_filter(self):
        response = await self.client.post("/api/host-filter/", headers=self.headers,
                                          json={
                                              "name": "test-http-view",
                                              "description": "none",
                                              "filters": [
                                                  {
                                                      "idc": {
                                                          "is": "idc1"
                                                      }
                                                  },
                                                  {
                                                      "env": {
                                                          "is": "test"
                                                      }
                                                  },
                                                  {
                                                      "ip": {
                                                          "in": [
                                                              "10.0.0.64",
                                                              "10.0.0.106"
                                                          ]
                                                      }
                                                  }
                                              ]
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        meta = result["data"]
        self.assertIsInstance(meta, dict)

        response = await self.client.get(f"/api/host-filter/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertDictEqual(meta, result["data"])

        response = await self.client.post(f"/api/host-filter/{meta['id']}/fork/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        fork_meta = result["data"]

        response = await self.client.get("/api/host-filter/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertIn(meta, result["data"])
        self.assertIn(fork_meta, result["data"])

        response = await self.client.delete(f"/api/host-filter/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        response = await self.client.delete(f"/api/host-filter/{fork_meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        response = await self.client.get("/api/host-filter/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertNotIn(meta, result["data"])

    @unittest_run_loop
    async def test_workflow(self):
        response = await self.client.post("/api/workflow/", headers=self.headers,
                                          json={
                                              "name": "test-http-view",
                                              "description": "none",
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        meta = result["data"]
        self.assertIsInstance(meta, dict)

        response = await self.client.get(f"/api/workflow/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertDictEqual(meta, result["data"])

        response = await self.client.post(f"/api/workflow/{meta['id']}/fork/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        fork_meta = result["data"]

        response = await self.client.get("/api/workflow/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertIn(meta, result["data"])
        self.assertIn(fork_meta, result["data"])

        response = await self.client.delete(f"/api/workflow/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        response = await self.client.delete(f"/api/workflow/{fork_meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        response = await self.client.get("/api/workflow/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertNotIn(meta, result["data"])

    @unittest_run_loop
    async def test_operator(self):
        response = await self.client.post("/api/operator/", headers=self.headers,
                                          json={
                                              "name": "test-http-view",
                                              "description": "none",
                                              "type": OPERATOR_TYPE_CELERY_REDIS,
                                              "mq_link": {
                                                  "link_kwargs": {
                                                      "address": ["redis", 6379],
                                                      "db": 11,
                                                      "password": None
                                                  }},
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        meta = result["data"]
        self.assertIsInstance(meta, dict)

        response = await self.client.get(f"/api/operator/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertDictEqual(meta, result["data"])

        response = await self.client.get("/api/operator/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertIn(meta, result["data"])

        response = await self.client.delete(f"/api/operator/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        response = await self.client.get("/api/operator/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertNotIn(meta, result["data"])

    @unittest_run_loop
    async def test_operation(self):
        response = await self.client.post("/api/operator/", headers=self.headers,
                                          json={
                                              "name": "test-http-view2",
                                              "description": "none",
                                              "type": OPERATOR_TYPE_CELERY_REDIS,
                                              "mq_link": {
                                                  "link_kwargs": {
                                                      "address": ["redis", 6379],
                                                      "db": 11,
                                                      "password": None
                                                  },
                                                  "broker": "redis://redis/7",
                                                  "backend": "redis://redis/8",
                                              },
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        operator = result["data"]
        self.assertIsInstance(operator, dict)

        response = await self.client.post("/api/host-filter/", headers=self.headers,
                                          json={
                                              "name": "test-http-view2",
                                              "description": "none",
                                              "filters": [
                                                  {
                                                      "idc": {
                                                          "is": "idc1"
                                                      }
                                                  },
                                                  {
                                                      "env": {
                                                          "is": "test"
                                                      }
                                                  },
                                              ]
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        host_filter = result["data"]
        self.assertIsInstance(host_filter, dict)

        response = await self.client.post("/api/workflow/", headers=self.headers,
                                          json={
                                              "name": "test-http-view2",
                                              "description": "none",
                                              "steps": [
                                                  {
                                                      "run_shell": {
                                                          "cmd": "rm -rf /tmp/host_tmp ; echo 'rm ok'",
                                                      },
                                                  },
                                                  {
                                                      "scp": {
                                                          "source": "/etc/hosts",
                                                          "dist": "/tmp/host_tmp"
                                                      }
                                                  },
                                                  {
                                                      "run_shell": {
                                                          "cmd": "cat /tmp/host_tmp",
                                                      }
                                                  }
                                              ]
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        workflow = result["data"]
        self.assertIsInstance(workflow, dict)

        # ---------------- operation -----------------

        response = await self.client.post("/api/operation/", headers=self.headers,
                                          json={
                                              "name": "test-http-view2",
                                              "description": "none",
                                              "host_filter_id": host_filter["id"],
                                              "workflow_id": workflow["id"],
                                              "operator_id": operator["id"],
                                          })
        self.assertEqual(response.status, 200)
        result = await response.json()
        logger.debug(result)
        self.assertEqual(result["code"], 0)
        meta = result["data"]
        self.assertIsInstance(meta, dict)

        response = await self.client.get(f"/api/operation/{meta['id']}/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)
        self.assertDictEqual(meta, result["data"])

        response = await self.client.post(f"/api/operation/{meta['id']}/refresh-cache/")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result["code"], 0)

        # response = await self.client.get("/api/operation/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)
        # self.assertIn(meta, result["data"])
        #
        # response = await self.client.delete(f"/api/operation/{meta['id']}/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)
        #
        # response = await self.client.get("/api/operation/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)
        # self.assertNotIn(meta, result["data"])
        #
        # # ---------------- operation -----------------
        #
        # response = await self.client.delete(f"/api/operator/{operator['id']}/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)
        #
        # response = await self.client.delete(f"/api/workflow/{workflow['id']}/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)
        #
        # response = await self.client.delete(f"/api/host-filter/{host_filter['id']}/")
        # self.assertEqual(response.status, 200)
        # result = await response.json()
        # self.assertEqual(result["code"], 0)


if __name__ == '__main__':
    unittest.main()
