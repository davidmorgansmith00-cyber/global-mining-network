using System.Net.Http;
using System.Text.Json;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Fetches maintenance.json and exposes the maintenance window state.
/// The launcher shows a banner when <see cref="MaintenanceInfo.IsActive"/> is true.
/// </summary>
public sealed class MaintenanceService
{
    private readonly HttpClient _http;

    public MaintenanceService(HttpClient http) => _http = http;

    /// <summary>
    /// Downloads maintenance status. Returns <see cref="MaintenanceInfo.None"/> on failure
    /// (fail-open: let the player attempt to launch even when the status endpoint is unreachable).
    /// </summary>
    public async Task<MaintenanceInfo> FetchAsync(ReleaseChannel channel,
        CancellationToken ct = default)
    {
        string url = $"{ChannelManager.GetChannelUrl(channel)}/maintenance.json";
        try
        {
            string json = await _http.GetStringAsync(url, ct).ConfigureAwait(false);
            return JsonSerializer.Deserialize<MaintenanceInfo>(json,
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
                ?? MaintenanceInfo.None;
        }
        catch
        {
            return MaintenanceInfo.None;
        }
    }
}

/// <summary>Maintenance window descriptor.</summary>
public sealed class MaintenanceInfo
{
    /// <summary>No active maintenance — fail-open sentinel.</summary>
    public static readonly MaintenanceInfo None = new();

    public bool IsActive { get; set; } = false;
    public string Message { get; set; } = string.Empty;
    public string StartsAt { get; set; } = string.Empty;
    public string EndsAt { get; set; } = string.Empty;
}
