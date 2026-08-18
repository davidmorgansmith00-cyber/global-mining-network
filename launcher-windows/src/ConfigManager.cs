using System.IO;
using System.Text.Json;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Reads and writes launcher.json from %LOCALAPPDATA%\GlobalMiningNetwork\launcher.json
/// </summary>
public sealed class ConfigManager
{
    private static readonly string ConfigDirectory = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "GlobalMiningNetwork");

    private static readonly string ConfigPath = Path.Combine(ConfigDirectory, "launcher.json");

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
    };

    /// <summary>
    /// Loads config from disk. Returns a default config if the file does not exist.
    /// </summary>
    public LauncherConfig Load()
    {
        if (!File.Exists(ConfigPath))
            return new LauncherConfig();

        string json = File.ReadAllText(ConfigPath);
        return JsonSerializer.Deserialize<LauncherConfig>(json, JsonOptions) ?? new LauncherConfig();
    }

    /// <summary>
    /// Persists config to disk. Creates the directory if it does not exist.
    /// </summary>
    public void Save(LauncherConfig config)
    {
        Directory.CreateDirectory(ConfigDirectory);
        string json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(ConfigPath, json);
    }

    /// <summary>
    /// Returns the path used for the config file on the current platform.
    /// </summary>
    public static string GetConfigPath() => ConfigPath;
}
