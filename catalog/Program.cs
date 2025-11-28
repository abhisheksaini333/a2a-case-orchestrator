using System.Text.Json.Nodes;

if (args.FirstOrDefault() == "health")
{
    using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
    try
    {
        var response = await client.GetAsync("http://127.0.0.1:" + (Environment.GetEnvironmentVariable("PORT") ?? "18132") + "/health");
        Environment.Exit(response.IsSuccessStatusCode ? 0 : 1);
    }
    catch (HttpRequestException) { Environment.Exit(1); }
    catch (TaskCanceledException) { Environment.Exit(1); }
    return;
}
if (args.FirstOrDefault() == "evaluate")
{
    var input = JsonNode.Parse(Console.In.ReadToEnd())!.AsObject();
    Console.WriteLine(CatalogRules.Evaluate(input).ToJsonString());
    return;
}
await new AgentServer().Run();

static class CatalogRules
{
    public static JsonObject Evaluate(JsonObject input)
    {
        var description = input["description"]?.GetValue<string>() ?? "";
        if (description.Length > 4000) throw new ArgumentException("Description exceeds 4000 characters");
        var words = description.ToLowerInvariant().Split(new[] { ' ', ',', '.', '-', '\n' }, StringSplitOptions.RemoveEmptyEntries);
        var category = words.Intersect(new[] { "laptop", "software", "server", "computer", "cloud" }).Any() ? "technology"
            : words.Intersect(new[] { "industrial", "machine", "bearings", "steel" }).Any() ? "industrial" : "office";
        var risk = words.Intersect(new[] { "sanctioned", "weapons", "prohibited" }).Any() ? "blocked" : "low";
        return new JsonObject { ["category"] = category, ["risk"] = risk };
    }
}
