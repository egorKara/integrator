import json
import tempfile
import unittest
from pathlib import Path

from agent_memory_routes import DEFAULT_AGENT_MEMORY_ROUTES, load_gateway_routes, resolve_route


class AgentMemoryRoutesTests(unittest.TestCase):
    def test_load_gateway_routes_overrides_known_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "gateway.json"
            p.write_text(json.dumps({"routes": {"memory_write": "/x"}}, ensure_ascii=False), encoding="utf-8")
            routes = load_gateway_routes(str(p))
        self.assertEqual(routes["memory_write"], "/x")
        self.assertEqual(routes["memory_search"], DEFAULT_AGENT_MEMORY_ROUTES["memory_search"])

    def test_resolve_route_falls_back(self) -> None:
        self.assertEqual(resolve_route({}, "memory_write"), DEFAULT_AGENT_MEMORY_ROUTES["memory_write"])
