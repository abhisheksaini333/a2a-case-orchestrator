using System.Text.Json.Nodes;

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
