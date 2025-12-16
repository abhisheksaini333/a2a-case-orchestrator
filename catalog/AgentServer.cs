using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

sealed class CapacityException : Exception { }
sealed class ProtocolException(int code, string message) : Exception(message) { public int Code { get; } = code; }

sealed class AgentServer
{
    private readonly string token = Environment.GetEnvironmentVariable("AGENT_TOKEN") ?? "";
    private readonly Dictionary<string, JsonObject> tasks = new();
    private readonly Dictionary<string, string> messages = new();
    private readonly Dictionary<string, string> requestDigests = new();
    private readonly object gate = new();
    private readonly string url;
    private readonly string statePath;
    private readonly HashSet<string> allowedHosts;
    private readonly HashSet<string> allowedOrigins;
    private readonly int maxTasks = int.Parse(Environment.GetEnvironmentVariable("MAX_TASKS") ?? "1000");
    private readonly int deadlineMs = int.Parse(Environment.GetEnvironmentVariable("REQUEST_DEADLINE_MS") ?? "10000");
    private readonly SemaphoreSlim admission = new(int.Parse(Environment.GetEnvironmentVariable("MAX_REQUESTS") ?? "16"));
    public AgentServer()
    {
        if (token.Length < 32) throw new ArgumentException("AGENT_TOKEN requires at least 32 characters");
        url = Environment.GetEnvironmentVariable("PUBLIC_URL") ?? "http://127.0.0.1:" + (Environment.GetEnvironmentVariable("PORT") ?? "18132");
        var port = Environment.GetEnvironmentVariable("PORT") ?? "18132";
        var publicUri = new Uri(url, UriKind.Absolute);
        if (publicUri.Scheme is not ("http" or "https") || publicUri.UserInfo.Length > 0)
            throw new ArgumentException("PUBLIC_URL requires an HTTP(S) service origin");
        allowedHosts = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "127.0.0.1:" + port, "localhost:" + port, publicUri.Authority
        };
        allowedOrigins = new HashSet<string>(StringComparer.Ordinal)
        {
            "http://127.0.0.1:" + port, "http://localhost:" + port,
            publicUri.GetLeftPart(UriPartial.Authority)
        };
        var directory = Environment.GetEnvironmentVariable("CATALOG_STATE") ?? ".runtime/catalog";
        Directory.CreateDirectory(directory); statePath = Path.Combine(directory, "tasks.json");
        if (File.Exists(statePath))
        {
            if (new FileInfo(statePath).Length > 16 * 1024 * 1024) throw new ArgumentException("Catalog journal exceeds 16 MiB");
            var saved = JsonNode.Parse(File.ReadAllText(statePath))!.AsObject();
            if (saved["tasks"]!.AsObject().Count > maxTasks) throw new ArgumentException("Catalog journal exceeds MAX_TASKS; archive before starting");
            foreach (var entry in saved["tasks"]!.AsObject()) tasks.Add(entry.Key, entry.Value!.DeepClone().AsObject());
            foreach (var entry in saved["messages"]!.AsObject()) messages.Add(entry.Key, entry.Value!.GetValue<string>());
            foreach (var entry in saved["requests"]!.AsObject()) requestDigests.Add(entry.Key, entry.Value!.GetValue<string>());
        }
    }
    public async Task Run()
    {
        var builder = WebApplication.CreateSlimBuilder();
        builder.Logging.ClearProviders();
        builder.WebHost.ConfigureKestrel(options =>
        {
            options.Limits.MaxConcurrentConnections = 32;
            options.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(2);
            options.Limits.KeepAliveTimeout = TimeSpan.FromSeconds(5);
            options.Limits.MaxRequestBodySize = 65536;
            options.Limits.MaxRequestHeadersTotalSize = 8192;
        });
        var app = builder.Build();
        app.Run(async context =>
        {
            if (!await admission.WaitAsync(0))
            {
                await Send(context, 503, new JsonObject { ["error"] = "capacity_limit" }); return;
            }
            try { await Handle(context); }
            finally { admission.Release(); }
        });
        var bind = Environment.GetEnvironmentVariable("BIND_ADDRESS") ?? "127.0.0.1";
        await app.RunAsync("http://" + bind + ":" + (Environment.GetEnvironmentVariable("PORT") ?? "18132"));
    }
    private JsonObject Card() => new()
    {
        ["protocolVersion"] = "0.3.0",
        ["preferredTransport"] = "JSONRPC",
        ["name"] = "catalog",
        ["description"] = "Supplier catalog matching service",
        ["url"] = url + "/a2a",
        ["version"] = "1.0.0",
        ["capabilities"] = new JsonObject { ["streaming"] = false, ["pushNotifications"] = false },
        ["defaultInputModes"] = new JsonArray("application/json"),
        ["defaultOutputModes"] = new JsonArray("application/json"),
        ["securitySchemes"] = new JsonObject { ["bearer"] = new JsonObject { ["type"] = "http", ["scheme"] = "bearer" } },
        ["security"] = new JsonArray(new JsonObject { ["bearer"] = new JsonArray() }),
        ["skills"] = new JsonArray(new JsonObject { ["id"] = "catalog-match", ["name"] = "Catalog matching", ["description"] = "Classify supplier goods and apply a local risk rule", ["tags"] = new JsonArray("supplier", "catalog") })
    };
    private async Task Handle(HttpContext context)
    {
        var request = context.Request; JsonNode? id = null;
        try
        {
            if (request.Headers.Host.Count != 1 || request.Headers.Authorization.Count > 1 || request.Headers.Origin.Count > 1)
            {
                await Send(context, 400, new JsonObject { ["error"] = "ambiguous_headers" });
                return;
            }
            if (!allowedHosts.Contains(request.Host.Value) ||
                (request.Headers.Origin.Count == 1 && !allowedOrigins.Contains(request.Headers.Origin.ToString())))
            {
                await Send(context, 403, new JsonObject { ["error"] = "untrusted_origin" });
                return;
            }
            if (request.Method == "GET" && request.Path == "/health") { await Send(context, 200, new JsonObject { ["status"] = "ok", ["service"] = "catalog" }); return; }
            if (request.Method == "GET" && (request.Path == "/.well-known/agent.json" || request.Path == "/.well-known/agent-card.json")) { await Send(context, 200, Card()); return; }
            var auth = request.Headers.Authorization.ToString();
            if (!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(auth), Encoding.UTF8.GetBytes("Bearer " + token))) { await Send(context, 401, new JsonObject { ["error"] = "unauthorized" }); return; }
            if (request.Method != "POST" || (request.Path != "/a2a" && request.Path != "/direct")) { await Send(context, 404, new JsonObject { ["error"] = "not_found" }); return; }
            if (request.Headers.ContainsKey("Transfer-Encoding")) { await Send(context, 400, new JsonObject { ["error"] = "unsupported_transfer_encoding" }); return; }
            if (request.ContentLength is null or <= 0 or > 65536) { await Send(context, 413, new JsonObject { ["error"] = "body_limit" }); return; }
            if (request.ContentType?.Split(';')[0] != "application/json") { await Send(context, 415, new JsonObject { ["error"] = "json_required" }); return; }
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted);
            deadline.CancelAfter(deadlineMs);
            var envelope = (await JsonNode.ParseAsync(request.Body, cancellationToken: deadline.Token))?.AsObject() ?? throw new ArgumentException("JSON object required");
            if (request.Path == "/direct")
            {
                if (envelope.Any(x => !new[] { "data", "contextId", "messageId", "taskId" }.Contains(x.Key))) throw new ArgumentException("Plain data request required");
                var message = new JsonObject
                {
                    ["kind"] = "message",
                    ["role"] = "user",
                    ["contextId"] = envelope["contextId"]?.DeepClone(),
                    ["messageId"] = envelope["messageId"]?.DeepClone(),
                    ["parts"] = new JsonArray(new JsonObject { ["kind"] = "data", ["data"] = envelope["data"]?.DeepClone() })
                };
                if (envelope["taskId"] != null) message["taskId"] = envelope["taskId"]!.DeepClone();
                JsonObject direct;
                lock (gate) direct = Dispatch("message/send", new JsonObject { ["message"] = message });
                await Send(context, 200, direct); return;
            }
            id = envelope["id"]?.DeepClone();
            if (envelope["jsonrpc"]?.GetValue<string>() != "2.0") throw new ArgumentException("JSON-RPC 2.0 required");
            JsonObject result;
            lock (gate) result = Dispatch(envelope["method"]?.GetValue<string>() ?? "", envelope["params"]?.AsObject() ?? new());
            await Send(context, 200, new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id, ["result"] = result });
        }
        catch (ProtocolException error)
        {
            await Send(context, 200, new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id, ["error"] = new JsonObject { ["code"] = error.Code, ["message"] = error.Message } });
        }
        catch (CapacityException)
        {
            await Send(context, 503, new JsonObject { ["error"] = "catalog_capacity_limit" });
        }
        catch (OperationCanceledException)
        {
            if (!context.RequestAborted.IsCancellationRequested) await Send(context, 408, new JsonObject { ["error"] = "request_deadline" });
        }
        catch (Exception error) when (error is ArgumentException or JsonException or InvalidOperationException or KeyNotFoundException)
        {
            await Send(context, 200, new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id, ["error"] = new JsonObject { ["code"] = -32602, ["message"] = "Invalid or unsupported catalog request" } });
        }
        catch (Exception)
        {
            if (!context.Response.HasStarted) await Send(context, 500, new JsonObject { ["error"] = "internal_service_error" });
            else context.Abort();
        }
    }
    private JsonObject Dispatch(string method, JsonObject parameters)
    {
        if (method is "tasks/get" or "tasks/cancel")
        {
            var lookupId = parameters["id"]?.GetValue<string>() ?? throw new ArgumentException("Task ID required");
            if (!tasks.TryGetValue(lookupId, out var found)) throw new ProtocolException(-32001, "Task not found");
            if (method == "tasks/cancel") throw new ProtocolException(-32002, "Completed catalog task cannot be canceled");
            return found.DeepClone().AsObject();
        }
        if (method != "message/send") throw new ProtocolException(-32601, "Method not supported");
        var message = parameters["message"]!.AsObject();
        if (message["kind"]?.GetValue<string>() != "message" || message["role"]?.GetValue<string>() != "user") throw new ArgumentException("User message required");
        var messageId = message["messageId"]!.GetValue<string>(); var contextId = message["contextId"]!.GetValue<string>();
        if (messageId.Length is < 1 or > 100 || contextId.Length is < 1 or > 100) throw new ArgumentException("Bounded identifiers required");
        var parts = message["parts"]!.AsArray();
        if (parts.Count != 1 || parts[0]?["kind"]?.GetValue<string>() != "data") throw new ArgumentException("One data part required");
        var data = parts[0]!["data"]!.AsObject();
        if (message["taskId"] != null) throw new ArgumentException("Completed catalog tasks cannot resume");
        var requestDigest = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(contextId + Artifact.Canonical(data))));
        if (messages.TryGetValue(messageId, out var prior))
        {
            if (requestDigests[messageId] != requestDigest) throw new ArgumentException("Message content changed");
            return tasks[prior].DeepClone().AsObject();
        }
        if (tasks.Count >= maxTasks) throw new CapacityException();
        var taskId = Guid.NewGuid().ToString("N"); var result = CatalogRules.Evaluate(data);
        var task = new JsonObject
        {
            ["kind"] = "task",
            ["id"] = taskId,
            ["contextId"] = contextId,
            ["status"] = new JsonObject { ["state"] = "completed" },
            ["artifacts"] = new JsonArray(Artifact.Sign(taskId, contextId, result))
        };
        tasks[taskId] = task; messages[messageId] = taskId; requestDigests[messageId] = requestDigest;
        try { Persist(); }
        catch { tasks.Remove(taskId); messages.Remove(messageId); requestDigests.Remove(messageId); throw; }
        return task.DeepClone().AsObject();
    }
    private void Persist()
    {
        var state = new JsonObject { ["tasks"] = new JsonObject(), ["messages"] = new JsonObject(), ["requests"] = new JsonObject() };
        foreach (var entry in tasks) state["tasks"]![entry.Key] = entry.Value.DeepClone();
        foreach (var entry in messages) state["messages"]![entry.Key] = entry.Value;
        foreach (var entry in requestDigests) state["requests"]![entry.Key] = entry.Value;
        var temporary = statePath + ".tmp";
        using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None))
        {
            var bytes = Encoding.UTF8.GetBytes(state.ToJsonString()); stream.Write(bytes); stream.Flush(true);
        }
        File.Move(temporary, statePath, true);
    }
    private static async Task Send(HttpContext context, int status, JsonNode data)
    {
        var bytes = Encoding.UTF8.GetBytes(data.ToJsonString());
        context.Response.StatusCode = status; context.Response.ContentType = "application/json";
        context.Response.Headers.CacheControl = "no-store"; context.Response.Headers["X-Content-Type-Options"] = "nosniff";
        context.Response.Headers["X-Frame-Options"] = "DENY";
        context.Response.Headers.ContentSecurityPolicy = "default-src 'none'; frame-ancestors 'none'";
        context.Response.ContentLength = bytes.Length;
        await context.Response.Body.WriteAsync(bytes, context.RequestAborted);
    }
}
