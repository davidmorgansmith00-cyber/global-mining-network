using System.Net.Http;
using System.Text.Json;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Fetches the patch notes JSON from {channel_url}/patch-notes.json and deserialises it.
/// </summary>
public sealed class PatchNotesService
{
    private readonly HttpClient _http;

    public PatchNotesService(HttpClient http) => _http = http;

    /// <summary>
    /// Downloads and returns patch notes for the given channel.
    /// Returns an empty list on failure.
    /// </summary>
    public async Task<IReadOnlyList<PatchNote>> FetchAsync(ReleaseChannel channel,
        CancellationToken ct = default)
    {
        string url = $"{ChannelManager.GetChannelUrl(channel)}/patch-notes.json";
        try
        {
            string json = await _http.GetStringAsync(url, ct).ConfigureAwait(false);
            var notes = JsonSerializer.Deserialize<List<PatchNote>>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
            return notes ?? [];
        }
        catch
        {
            return [];
        }
    }
}

/// <summary>A single patch-note entry.</summary>
public sealed class PatchNote
{
    public string Version { get; set; } = string.Empty;
    public string Date { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Body { get; set; } = string.Empty;
}
