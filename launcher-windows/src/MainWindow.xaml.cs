using System.Net.Http;
using System.Windows;
using System.Windows.Controls;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Main launcher window: displays patch notes, maintenance alerts and the launch button.
/// </summary>
public partial class MainWindow : Window
{
    private readonly ConfigManager _configManager = new();
    private readonly ChannelManager _channelManager = new();
    private readonly GameLauncher _gameLauncher = new();
    private readonly HttpClient _httpClient = new();
    private PatchNotesService? _patchNotesService;
    private MaintenanceService? _maintenanceService;
    private LauncherConfig _config = new();

    public MainWindow()
    {
        InitializeComponent();
        Loaded += async (_, _) => await InitialiseAsync();
    }

    // ─── Initialisation ─────────────────────────────────────────────────────

    private async Task InitialiseAsync()
    {
        _config = _configManager.Load();
        _patchNotesService = new PatchNotesService(_httpClient);
        _maintenanceService = new MaintenanceService(_httpClient);

        PopulateChannelSelector();
        UpdateStatusLabels();

        var channel = ChannelManager.Parse(_config.Channel);
        await RefreshMaintenanceAsync(channel);
        await RefreshPatchNotesAsync(channel);
    }

    private void PopulateChannelSelector()
    {
        ChannelSelector.Items.Clear();
        foreach (ReleaseChannel ch in Enum.GetValues<ReleaseChannel>())
            ChannelSelector.Items.Add(ChannelManager.ToConfigString(ch));

        ChannelSelector.SelectedItem = _config.Channel;
    }

    private void UpdateStatusLabels()
    {
        VersionLabel.Text = $"Version: {_config.CurrentVersion}";
        ChannelLabel.Text = $"Channel: {_config.Channel}";
    }

    // ─── Maintenance ────────────────────────────────────────────────────────

    private async Task RefreshMaintenanceAsync(ReleaseChannel channel)
    {
        var maintenance = await _maintenanceService!.FetchAsync(channel);
        if (maintenance.IsActive)
        {
            MaintenanceBannerText.Text = maintenance.Message.Length > 0
                ? maintenance.Message
                : "Scheduled maintenance is active.";
            MaintenanceBanner.Visibility = Visibility.Visible;
            LaunchButton.IsEnabled = false;
            StatusBarText.Text = "Server maintenance in progress.";
        }
        else
        {
            MaintenanceBanner.Visibility = Visibility.Collapsed;
            LaunchButton.IsEnabled = true;
            StatusBarText.Text = "Ready to launch";
        }
    }

    // ─── Patch Notes ─────────────────────────────────────────────────────────

    private async Task RefreshPatchNotesAsync(ReleaseChannel channel)
    {
        PatchNotesLoading.Text = "Loading patch notes…";
        PatchNotesLoading.Visibility = Visibility.Visible;

        var notes = await _patchNotesService!.FetchAsync(channel);

        PatchNotesLoading.Visibility = Visibility.Collapsed;

        foreach (var note in notes)
        {
            var header = new TextBlock
            {
                Text = $"[{note.Date}]  {note.Version} — {note.Title}",
                Foreground = System.Windows.Media.Brushes.White,
                FontSize = 13,
                FontWeight = FontWeights.Bold,
                TextWrapping = TextWrapping.Wrap,
            };
            var body = new TextBlock
            {
                Text = note.Body,
                Foreground = System.Windows.Media.Brushes.Gray,
                FontSize = 12,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 2, 0, 8),
            };
            PatchNotesPanel.Children.Add(header);
            PatchNotesPanel.Children.Add(body);
        }

        if (notes.Count == 0)
        {
            PatchNotesLoading.Text = "No patch notes available.";
            PatchNotesLoading.Visibility = Visibility.Visible;
        }
    }

    // ─── Event Handlers ──────────────────────────────────────────────────────

    private async void ChannelSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ChannelSelector.SelectedItem is string selected)
        {
            _channelManager.SwitchChannel(_configManager, ChannelManager.Parse(selected));
            _config = _configManager.Load();
            UpdateStatusLabels();
            await RefreshMaintenanceAsync(ChannelManager.Parse(selected));
            await RefreshPatchNotesAsync(ChannelManager.Parse(selected));
        }
    }

    private void LaunchButton_Click(object sender, RoutedEventArgs e)
    {
        string exe = System.IO.Path.Combine(_config.InstallPath, "gmn_client.exe");
        string token = _config.SessionToken ?? string.Empty;

        if (string.IsNullOrEmpty(token))
        {
            StatusBarText.Text = "Please log in before launching.";
            return;
        }

        if (!_gameLauncher.Launch(exe, token, _config.InstallPath))
        {
            StatusBarText.Text = "Failed to start the game. Check the install path.";
            return;
        }

        LaunchButton.IsEnabled = false;
        StatusBarText.Text = "Game running…";
        _gameLauncher.GameExited += (_, _) =>
        {
            Dispatcher.Invoke(() =>
            {
                LaunchButton.IsEnabled = true;
                StatusBarText.Text = "Game closed. Ready to launch.";
            });
        };
    }

    private void AccountButton_Click(object sender, RoutedEventArgs e)
    {
        var accountManager = new AccountManager(_configManager);
        accountManager.ShowLoginWindow();
    }

    private void SettingsButton_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show("Settings — coming soon.", "Settings",
            MessageBoxButton.OK, MessageBoxImage.Information);
    }
}
