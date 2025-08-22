using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;

static class Artifact
{
    public static string Canonical(JsonNode? value)
    {
        if (value is JsonObject obj)
            return "{" + string.Join(",", obj.OrderBy(x => x.Key, StringComparer.Ordinal).Select(x => JsonSerializer.Serialize(x.Key) + ":" + Canonical(x.Value))) + "}";
        if (value is JsonArray array) return "[" + string.Join(",", array.Select(Canonical)) + "]";
        return value?.ToJsonString(new JsonSerializerOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping }) ?? "null";
    }
    public static JsonObject Sign(string taskId, string contextId, JsonObject data)
    {
        var key = Environment.GetEnvironmentVariable("ARTIFACT_KEY") ?? "";
        if (key.Length < 32) throw new ArgumentException("ARTIFACT_KEY requires at least 32 characters");
        var signed = new JsonObject { ["owner"] = "catalog", ["taskId"] = taskId, ["contextId"] = contextId, ["data"] = data.DeepClone() };
        var signature = Convert.ToHexString(HMACSHA256.HashData(Encoding.UTF8.GetBytes(key), Encoding.UTF8.GetBytes(Canonical(signed)))).ToLowerInvariant();
        return new JsonObject {
            ["artifactId"] = Guid.NewGuid().ToString("N"), ["name"] = "catalog evidence",
            ["parts"] = new JsonArray(new JsonObject { ["kind"] = "data", ["data"] = data.DeepClone() }),
            ["metadata"] = new JsonObject { ["owner"] = "catalog", ["taskId"] = taskId, ["contextId"] = contextId, ["signature"] = signature }
        };
    }
}
