using System.Text.Json.Serialization;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Config model matching launcher.json schema.
/// Stored at %LOCALAPPDATA%\GlobalMiningNetwork\launcher.json
/// </summary>
public sealed class LauncherConfig
{
    [JsonPropertyName("version")]
    public string Version { get; set; } = "1.0";

    [JsonPropertyName("install_path")]
    public string InstallPath { get; set; } = @"C:\Program Files\GlobalMiningNetwork";

    [JsonPropertyName("channel")]
    public string Channel { get; set; } = "stable";

    [JsonPropertyName("last_version")]
    public string LastVersion { get; set; } = "0.1.0";

    [JsonPropertyName("current_version")]
    public string CurrentVersion { get; set; } = "0.1.0";

    [JsonPropertyName("session_token")]
    public string? SessionToken { get; set; }

    [JsonPropertyName("session_expires_at")]
    public string? SessionExpiresAt { get; set; }

    [JsonPropertyName("last_update_check")]
    public string? LastUpdateCheck { get; set; }

    [JsonPropertyName("accessibility")]
    public AccessibilitySettingsData? Accessibility { get; set; }
}
