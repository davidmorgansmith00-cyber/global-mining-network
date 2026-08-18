using System.Text.Json.Serialization;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Accessibility settings data stored under the "accessibility" key in launcher.json.
/// </summary>
public sealed class AccessibilitySettingsData
{
    /// <summary>UI scale factor. 1.0 = 100% (default). Range 0.75–2.0.</summary>
    [JsonPropertyName("ui_scale")]
    public double UIScale { get; set; } = 1.0;

    /// <summary>Text size modifier applied on top of UIScale. Range 0.75–2.0.</summary>
    [JsonPropertyName("text_size")]
    public double TextSize { get; set; } = 1.0;

    /// <summary>When true, the high-contrast palette is active.</summary>
    [JsonPropertyName("high_contrast")]
    public bool HighContrast { get; set; } = false;

    /// <summary>
    /// Color-blind mode. Accepted values: "none", "deuteranopia", "protanopia".
    /// </summary>
    [JsonPropertyName("color_blind_mode")]
    public string ColorBlindMode { get; set; } = "none";

    /// <summary>When true, animations and motion effects are reduced.</summary>
    [JsonPropertyName("reduce_motion")]
    public bool ReduceMotion { get; set; } = false;
}

/// <summary>
/// Service that loads, validates and persists accessibility settings through ConfigManager.
/// </summary>
public sealed class AccessibilitySettings
{
    private static readonly AccessibilitySettingsData Defaults = new();

    private readonly ConfigManager _configManager;

    public AccessibilitySettings(ConfigManager configManager) =>
        _configManager = configManager;

    /// <summary>Loads accessibility settings from the launcher config.</summary>
    public AccessibilitySettingsData Load()
    {
        var config = _configManager.Load();
        return config.Accessibility ?? Defaults;
    }

    /// <summary>Saves accessibility settings, validating ranges first.</summary>
    public void Save(AccessibilitySettingsData settings)
    {
        Validate(settings);
        var config = _configManager.Load();
        config.Accessibility = settings;
        _configManager.Save(config);
    }

    // ─── Validation ─────────────────────────────────────────────────────────

    /// <summary>Throws <see cref="ArgumentOutOfRangeException"/> when any value is out of range.</summary>
    public static void Validate(AccessibilitySettingsData settings)
    {
        if (settings.UIScale < 0.75 || settings.UIScale > 2.0)
            throw new ArgumentOutOfRangeException(nameof(settings.UIScale),
                $"UIScale must be between 0.75 and 2.0 (got {settings.UIScale}).");

        if (settings.TextSize < 0.75 || settings.TextSize > 2.0)
            throw new ArgumentOutOfRangeException(nameof(settings.TextSize),
                $"TextSize must be between 0.75 and 2.0 (got {settings.TextSize}).");

        var validModes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            { "none", "deuteranopia", "protanopia" };
        if (!validModes.Contains(settings.ColorBlindMode))
            throw new ArgumentException(
                $"ColorBlindMode '{settings.ColorBlindMode}' is not recognised.",
                nameof(settings.ColorBlindMode));
    }
}
