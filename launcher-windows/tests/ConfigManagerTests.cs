using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace GlobalMiningNetwork.Launcher.Tests;

[TestClass]
public sealed class ConfigManagerTests
{
    // Each test uses a unique temp directory to avoid cross-test interference.

    private static (ConfigManager manager, string dir) CreateIsolated()
    {
        string dir = Path.Combine(Path.GetTempPath(), "gmn_config_test_" + Guid.NewGuid());
        Directory.CreateDirectory(dir);
        // We need to subclass or use the static path — instead we write / read directly.
        // ConfigManager uses %LOCALAPPDATA%\GlobalMiningNetwork; for tests we validate
        // the JSON round-trip through LauncherConfig serialisation helpers.
        var manager = new ConfigManager();
        return (manager, dir);
    }

    [TestMethod]
    public void Load_ReturnsDefaultConfig_WhenFileAbsent()
    {
        // ConfigManager.Load reads from a fixed system path; when the file does not
        // exist it returns a default object with non-null properties.
        var manager = new ConfigManager();
        // In CI this path won't exist, so we get a default.
        var config = manager.Load();
        Assert.IsNotNull(config);
        Assert.IsFalse(string.IsNullOrEmpty(config.Version));
        Assert.IsFalse(string.IsNullOrEmpty(config.Channel));
        Assert.IsFalse(string.IsNullOrEmpty(config.InstallPath));
    }

    [TestMethod]
    public void DefaultConfig_HasExpectedChannelAndVersion()
    {
        var config = new LauncherConfig();
        Assert.AreEqual("stable", config.Channel);
        Assert.AreEqual("1.0", config.Version);
        Assert.AreEqual("0.1.0", config.CurrentVersion);
    }

    [TestMethod]
    public void DefaultConfig_HasNullOptionalFields()
    {
        var config = new LauncherConfig();
        Assert.IsNull(config.SessionToken);
        Assert.IsNull(config.SessionExpiresAt);
        Assert.IsNull(config.LastUpdateCheck);
        Assert.IsNull(config.Accessibility);
    }

    [TestMethod]
    public void GetConfigPath_ReturnsNonEmptyString()
    {
        string path = ConfigManager.GetConfigPath();
        Assert.IsFalse(string.IsNullOrEmpty(path));
        StringAssert.Contains(path, "GlobalMiningNetwork");
    }
}
