"""Pinned-endpoint A2A client. Cards never choose arbitrary network destinations."""

import json
import urllib.request
import urllib.error
import uuid
from .domain import DomainError


class PinnedEndpointRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise DomainError(
            "agent_redirect", "Configured agent endpoints must not redirect"
        )


class Client:
    def __init__(self, url, token, name, skill):
        self.url, self.token, self.name, self.skill = (
            url.rstrip("/"),
            token,
            name,
            skill,
        )
        self.measurements = {"requests": 0, "request_bytes": 0, "response_bytes": 0}

    def fetch(self, path, data=None):
        request = urllib.request.Request(
            self.url + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
            },
        )
        self.measurements["requests"] += 1
        self.measurements["request_bytes"] += len(request.data or b"")
        try:
            with urllib.request.build_opener(PinnedEndpointRedirect()).open(
                request, timeout=10
            ) as response:
                raw = response.read(1048577)
                self.measurements["response_bytes"] += len(raw)
                if len(raw) > 1048576:
                    raise DomainError(
                        "response_limit", "Agent response exceeded its size limit"
                    )
                return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DomainError(
                "agent_unavailable",
                f"{self.name} service could not be reached or returned invalid JSON",
            ) from exc

    def discover(self):
        card = self.fetch("/.well-known/agent.json")
        if (
            not isinstance(card, dict)
            or not isinstance(card.get("skills"), list)
            or any(
                not isinstance(skill, dict) or not isinstance(skill.get("id"), str)
                for skill in card["skills"]
            )
            or not isinstance(card.get("defaultInputModes"), list)
            or any(not isinstance(mode, str) for mode in card["defaultInputModes"])
            or not isinstance(card.get("protocolVersion", "0.2.0"), str)
        ):
            raise DomainError(
                "invalid_agent_card", "Agent discovery returned a malformed card"
            )
        if card.get("name") != self.name or self.skill not in {
            s.get("id") for s in card.get("skills", [])
        }:
            raise DomainError(
                "skill_mismatch", "Discovered agent does not offer the configured skill"
            )
        if "application/json" not in card.get("defaultInputModes", []):
            raise DomainError(
                "mode_mismatch", "Agent cannot accept structured supplier records"
            )
        version = card.get("protocolVersion", "0.2.0")
        if (
            version not in {"0.2.0", "0.3.0"}
            or card.get("preferredTransport", "JSONRPC") != "JSONRPC"
        ):
            raise DomainError(
                "unsupported_profile",
                "Agent protocol revision or transport is not supported",
            )
        self.negotiated_version = version
        return card

    def rpc(self, method, params):
        request_id = uuid.uuid4().hex
        response = self.fetch(
            "/a2a",
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        )
        if (
            not isinstance(response, dict)
            or response.get("jsonrpc") != "2.0"
            or response.get("id") != request_id
            or (("result" in response) == ("error" in response))
        ):
            raise DomainError(
                "invalid_agent_response", "Agent response did not match the request"
            )
        if "error" in response:
            error = response["error"]
            if (
                not isinstance(error, dict)
                or type(error.get("code")) is not int
                or not isinstance(error.get("message"), str)
            ):
                raise DomainError(
                    "invalid_agent_response", "Agent returned a malformed error"
                )
            raise DomainError(
                "agent_error",
                str(response["error"].get("message", "Agent rejected the request")),
            )
        result = response.get("result")
        if not isinstance(result, dict) or result.get("kind") != "task":
            raise DomainError("invalid_agent_response", "Agent did not return a task")
        return result

    def send(self, data, context, message_id, task_id=None):
        message = {
            "kind": "message",
            "role": "user",
            "messageId": message_id,
            "contextId": context,
            "parts": [{"kind": "data", "data": data}],
        }
        if task_id:
            message["taskId"] = task_id
        result = self.rpc("message/send", {"message": message})
        if result.get("contextId") != context or (
            task_id and result.get("id") != task_id
        ):
            raise DomainError(
                "context_mismatch", "Agent changed the task or context binding"
            )
        return result


class DirectClient(Client):
    """Comparison adapter: simple JSON input/output, same durable application logic."""

    def discover(self):
        return {"name": self.name, "skill": self.skill, "configured": True}

    def send(self, data, context, message_id, task_id=None):
        payload = {"data": data, "contextId": context, "messageId": message_id}
        if task_id:
            payload["taskId"] = task_id
        result = self.fetch("/direct", payload)
        if (
            not isinstance(result, dict)
            or result.get("kind") != "task"
            or result.get("contextId") != context
            or (task_id and result.get("id") != task_id)
        ):
            raise DomainError(
                "invalid_agent_response", "Direct service changed the task binding"
            )
        return result
