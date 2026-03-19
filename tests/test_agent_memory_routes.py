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

    def test_load_gateway_routes_fallbacks_for_bad_input(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            missing = base / "missing.json"
            self.assertEqual(load_gateway_routes(str(missing)), DEFAULT_AGENT_MEMORY_ROUTES)

            bad_json = base / "bad.json"
            bad_json.write_text("{", encoding="utf-8")
            self.assertEqual(load_gateway_routes(str(bad_json)), DEFAULT_AGENT_MEMORY_ROUTES)

            not_object = base / "not_object.json"
            not_object.write_text(json.dumps(["x"]), encoding="utf-8")
            self.assertEqual(load_gateway_routes(str(not_object)), DEFAULT_AGENT_MEMORY_ROUTES)

            no_routes_dict = base / "no_routes_dict.json"
            no_routes_dict.write_text(json.dumps({"routes": []}), encoding="utf-8")
            self.assertEqual(load_gateway_routes(str(no_routes_dict)), DEFAULT_AGENT_MEMORY_ROUTES)

    def test_resolve_route_falls_back_on_invalid_value(self) -> None:
        self.assertEqual(
            resolve_route({"memory_write": "relative/path"}, "memory_write"),
            DEFAULT_AGENT_MEMORY_ROUTES["memory_write"],
        )
