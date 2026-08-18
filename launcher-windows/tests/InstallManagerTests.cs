using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace GlobalMiningNetwork.Launcher.Tests;

[TestClass]
public sealed class InstallManagerTests
{
    private readonly InstallManager _manager = new();

    [TestMethod]
    public void ValidateInstallPath_RejectsEmptyString()
    {
        bool result = _manager.ValidateInstallPath(string.Empty, out string reason);
        Assert.IsFalse(result);
        Assert.IsFalse(string.IsNullOrEmpty(reason));
    }

    [TestMethod]
    public void ValidateInstallPath_RejectsWhitespace()
    {
        bool result = _manager.ValidateInstallPath("   ", out string reason);
        Assert.IsFalse(result);
        Assert.IsFalse(string.IsNullOrEmpty(reason));
    }

    [TestMethod]
    public void RepairInstall_ReturnsFalseWhenDirectoryMissing()
    {
        string nonexistent = Path.Combine(Path.GetTempPath(), "gmn_repair_test_nonexistent_xyz");
        var result = _manager.RepairInstall(nonexistent);
        Assert.IsFalse(result.Success);
        Assert.IsFalse(string.IsNullOrEmpty(result.Message));
    }

    [TestMethod]
    public void RepairInstall_ReturnsTrueWhenDirectoryExists()
    {
        string tmpDir = Path.Combine(Path.GetTempPath(), "gmn_repair_test_" + Guid.NewGuid());
        Directory.CreateDirectory(tmpDir);
        try
        {
            var result = _manager.RepairInstall(tmpDir);
            Assert.IsTrue(result.Success);
        }
        finally
        {
            Directory.Delete(tmpDir, recursive: true);
        }
    }
}
