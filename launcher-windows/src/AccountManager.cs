using System.Windows;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Manages account UI flows: login, create account, password recovery,
/// session management and privacy settings.
/// </summary>
public sealed class AccountManager
{
    private readonly ConfigManager _configManager;

    public AccountManager(ConfigManager configManager) => _configManager = configManager;

    /// <summary>Shows the login dialog.</summary>
    public void ShowLoginWindow() =>
        MessageBox.Show("Login — account authentication UI coming in M4 Slice 2.",
            "Log In", MessageBoxButton.OK, MessageBoxImage.Information);

    /// <summary>Shows the create-account dialog.</summary>
    public void ShowCreateAccountWindow() =>
        MessageBox.Show("Create Account — registration UI coming in M4 Slice 2.",
            "Create Account", MessageBoxButton.OK, MessageBoxImage.Information);

    /// <summary>Shows the password recovery dialog.</summary>
    public void ShowPasswordRecoveryWindow() =>
        MessageBox.Show("Password Recovery — recovery UI coming in M4 Slice 2.",
            "Password Recovery", MessageBoxButton.OK, MessageBoxImage.Information);

    /// <summary>Shows the session management dialog.</summary>
    public void ShowSessionManagementWindow() =>
        MessageBox.Show("Session Management — device/session list coming in M4 Slice 2.",
            "Sessions", MessageBoxButton.OK, MessageBoxImage.Information);

    /// <summary>Shows the privacy settings dialog.</summary>
    public void ShowPrivacyWindow() =>
        MessageBox.Show("Privacy Settings — privacy controls coming in M4 Slice 2.",
            "Privacy Settings", MessageBoxButton.OK, MessageBoxImage.Information);
}
