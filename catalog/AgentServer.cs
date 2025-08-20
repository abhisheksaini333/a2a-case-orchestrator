using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

sealed class AgentServer
{
    private readonly string token = Environment.GetEnvironmentVariable("AGENT_TOKEN") ?? "";
    private readonly Dictionary<string, JsonObject> tasks = new();
    private readonly Dictionary<string, string> messages = new();
    private readonly object gate = new();
    private readonly string url;
    public AgentServer()
    {
        if (token.Length < 32) throw new ArgumentException("AGENT_TOKEN requires at least 32 characters");
        url = "http://127.0.0.1:" + (Environment.GetEnvironmentVariable("PORT") ?? "18132");
    }
    public async Task Run()
    {
        using var listener = new HttpListener();
        listener.Prefixes.Add(url + "/"); listener.Start();
        while (true)
        {
            var context = await listener.GetContextAsync();
            _ = Task.Run(() => Handle(context));
        }
    }
    private JsonObject Card() => new()
    {
        ["name"] = "catalog", ["description"] = "Supplier catalog matching service", ["url"] = url + "/a2a", ["version"] = "1.0.0",
        ["capabilities"] = new JsonObject { ["streaming"] = false, ["pushNotifications"] = false },
        ["defaultInputModes"] = new JsonArray("application/json"), ["defaultOutputModes"] = new JsonArray("application/json"),
        ["securitySchemes"] = new JsonObject { ["bearer"] = new JsonObject { ["type"] = "http", ["scheme"] = "bearer" } },
        ["security"] = new JsonArray(new JsonObject { ["bearer"] = new JsonArray() }),
        ["skills"] = new JsonArray(new JsonObject { ["id"] = "catalog-match", ["name"] = "Catalog matching", ["description"] = "Classify supplier goods and apply a local risk rule", ["tags"] = new JsonArray("supplier", "catalog") })
    };
    private async Task Handle(HttpListenerContext context)
    {
        var request = context.Request; JsonNode? id = null;
        try
        {
            if (request.HttpMethod == "GET" && request.Url!.AbsolutePath == "/health") { await Send(context, 200, new JsonObject { ["status"] = "ok", ["service"] = "catalog" }); return; }
            if (request.HttpMethod == "GET" && request.Url!.AbsolutePath == "/.well-known/agent.json") { await Send(context, 200, Card()); return; }
            var auth = request.Headers["Authorization"] ?? "";
            if (!CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(auth), Encoding.UTF8.GetBytes("Bearer " + token))) { await Send(context, 401, new JsonObject { ["error"] = "unauthorized" }); return; }
            if (request.HttpMethod != "POST" || request.Url!.AbsolutePath is not ("/a2a" or "/direct")) { await Send(context, 404, new JsonObject { ["error"] = "not_found" }); return; }
            if (request.ContentLength64 is <= 0 or > 65536) { await Send(context, 413, new JsonObject { ["error"] = "body_limit" }); return; }
            if (request.ContentType?.Split(';')[0] != "application/json") { await Send(context, 415, new JsonObject { ["error"] = "json_required" }); return; }
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            var envelope = (await JsonNode.ParseAsync(request.InputStream, cancellationToken: deadline.Token))?.AsObject() ?? throw new ArgumentException("JSON object required");
            id = envelope["id"]?.DeepClone();
            if (envelope["jsonrpc"]?.GetValue<string>() != "2.0") throw new ArgumentException("JSON-RPC 2.0 required");
            JsonObject result;
            lock (gate) result = Dispatch(envelope["method"]?.GetValue<string>() ?? "", envelope["params"]?.AsObject() ?? new());
            await Send(context, 200, new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id, ["result"] = result });
        }
        catch (Exception error) when (error is ArgumentException or JsonException or InvalidOperationException or KeyNotFoundException)
        {
            await Send(context, 200, new JsonObject { ["jsonrpc"] = "2.0", ["id"] = id, ["error"] = new JsonObject { ["code"] = -32602, ["message"] = "Invalid or unsupported catalog request" } });
        }
        catch (Exception)
        {
            try { await Send(context, 500, new JsonObject { ["error"] = "internal_service_error" }); } catch (Exception) { context.Response.Close(); }
        }
    }
    private JsonObject Dispatch(string method, JsonObject parameters)
    {
        if (method == "tasks/get") return tasks[parameters["id"]!.GetValue<string>()].DeepClone().AsObject();
        if (method != "message/send") throw new ArgumentException("Unsupported method");
        var message = parameters["message"]!.AsObject();
        if (message["kind"]?.GetValue<string>() != "message" || message["role"]?.GetValue<string>() != "user") throw new ArgumentException("User message required");
        var messageId = message["messageId"]!.GetValue<string>(); var contextId = message["contextId"]!.GetValue<string>();
        if (messageId.Length is < 1 or > 100 || contextId.Length is < 1 or > 100) throw new ArgumentException("Bounded identifiers required");
        var parts = message["parts"]!.AsArray();
        if (parts.Count != 1 || parts[0]?["kind"]?.GetValue<string>() != "data") throw new ArgumentException("One data part required");
        var data = parts[0]!["data"]!.AsObject();
        if (messages.TryGetValue(messageId, out var prior)) return tasks[prior].DeepClone().AsObject();
        var taskId = Guid.NewGuid().ToString("N"); var result = CatalogRules.Evaluate(data);
        var task = new JsonObject
        {
            ["kind"] = "task", ["id"] = taskId, ["contextId"] = contextId,
            ["status"] = new JsonObject { ["state"] = "completed" },
            ["artifacts"] = new JsonArray(new JsonObject { ["artifactId"] = Guid.NewGuid().ToString("N"), ["name"] = "catalog evidence", ["parts"] = new JsonArray(new JsonObject { ["kind"] = "data", ["data"] = result }) })
        };
        tasks[taskId] = task; messages[messageId] = taskId;
        return task.DeepClone().AsObject();
    }
    private static async Task Send(HttpListenerContext context, int status, JsonNode data)
    {
        var bytes = Encoding.UTF8.GetBytes(data.ToJsonString());
        context.Response.StatusCode = status; context.Response.ContentType = "application/json";
        context.Response.Headers["Cache-Control"] = "no-store"; context.Response.Headers["X-Content-Type-Options"] = "nosniff";
        context.Response.Headers["X-Frame-Options"] = "DENY";
        context.Response.ContentLength64 = bytes.Length;
        await context.Response.OutputStream.WriteAsync(bytes); context.Response.Close();
    }
}
