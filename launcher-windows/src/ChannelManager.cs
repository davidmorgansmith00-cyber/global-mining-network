namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Available release channels in priority order (lowest stability → highest stability).
/// </summary>
public enum ReleaseChannel
{
    Internal,
    Experimental,
    Beta,
    Stable,
}

/// <summary>
/// Manages channel selection and switching for the launcher.
/// </summary>
public sealed class ChannelManager
{
    private static readonly Dictionary<string, ReleaseChannel> ChannelMap =
        new(StringComparer.OrdinalIgnoreCase)
        {
            ["internal"]     = ReleaseChannel.Internal,
            ["experimental"] = ReleaseChannel.Experimental,
            ["beta"]         = ReleaseChannel.Beta,
            ["stable"]       = ReleaseChannel.Stable,
        };

    /// <summary>
    /// Parses a channel string from config. Returns <see cref="ReleaseChannel.Stable"/> as default.
    /// </summary>
    public static ReleaseChannel Parse(string? channelName)
    {
        if (channelName is not null && ChannelMap.TryGetValue(channelName, out var channel))
            return channel;
        return ReleaseChannel.Stable;
    }

    /// <summary>
    /// Returns the lowercase channel name used in config and CDN URLs.
    /// </summary>
    public static string ToConfigString(ReleaseChannel channel) =>
        channel.ToString().ToLowerInvariant();

    /// <summary>
    /// Returns the CDN base URL for the given channel. Channels are fictional/internal.
    /// </summary>
    public static string GetChannelUrl(ReleaseChannel channel) =>
        $"https://launcher.globalminingnetwork.invalid/{ToConfigString(channel)}";

    /// <summary>
    /// Switches the persisted channel in the launcher config and saves.
    /// </summary>
    public void SwitchChannel(ConfigManager configManager, ReleaseChannel newChannel)
    {
        LauncherConfig config = configManager.Load();
        config.Channel = ToConfigString(newChannel);
        configManager.Save(config);
    }
}
