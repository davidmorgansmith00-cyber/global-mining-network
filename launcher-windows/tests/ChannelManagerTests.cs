using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace GlobalMiningNetwork.Launcher.Tests;

[TestClass]
public sealed class ChannelManagerTests
{
    [TestMethod]
    public void Parse_ReturnsStable_ForUnrecognisedInput()
    {
        Assert.AreEqual(ReleaseChannel.Stable, ChannelManager.Parse(null));
        Assert.AreEqual(ReleaseChannel.Stable, ChannelManager.Parse("unknown"));
        Assert.AreEqual(ReleaseChannel.Stable, ChannelManager.Parse(""));
    }

    [TestMethod]
    public void Parse_IsCaseInsensitive()
    {
        Assert.AreEqual(ReleaseChannel.Beta, ChannelManager.Parse("BETA"));
        Assert.AreEqual(ReleaseChannel.Beta, ChannelManager.Parse("Beta"));
        Assert.AreEqual(ReleaseChannel.Internal, ChannelManager.Parse("INTERNAL"));
    }

    [TestMethod]
    public void Parse_ReturnsAllFourChannels()
    {
        Assert.AreEqual(ReleaseChannel.Internal,     ChannelManager.Parse("internal"));
        Assert.AreEqual(ReleaseChannel.Experimental, ChannelManager.Parse("experimental"));
        Assert.AreEqual(ReleaseChannel.Beta,         ChannelManager.Parse("beta"));
        Assert.AreEqual(ReleaseChannel.Stable,       ChannelManager.Parse("stable"));
    }

    [TestMethod]
    public void ToConfigString_ProducesLowercaseNames()
    {
        Assert.AreEqual("stable",       ChannelManager.ToConfigString(ReleaseChannel.Stable));
        Assert.AreEqual("beta",         ChannelManager.ToConfigString(ReleaseChannel.Beta));
        Assert.AreEqual("experimental", ChannelManager.ToConfigString(ReleaseChannel.Experimental));
        Assert.AreEqual("internal",     ChannelManager.ToConfigString(ReleaseChannel.Internal));
    }

    [TestMethod]
    public void GetChannelUrl_ContainsChannelName()
    {
        string url = ChannelManager.GetChannelUrl(ReleaseChannel.Beta);
        StringAssert.Contains(url, "beta");
    }
}
