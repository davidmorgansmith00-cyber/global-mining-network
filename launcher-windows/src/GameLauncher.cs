using System.Diagnostics;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Spawns the game client process with the authenticated session token and monitors it.
/// </summary>
public sealed class GameLauncher
{
    public event EventHandler? GameExited;

    private Process? _process;

    /// <summary>
    /// Launches the game client executable.
    /// </summary>
    /// <param name="executablePath">Full path to the game executable.</param>
    /// <param name="sessionToken">Server-issued session token.</param>
    /// <param name="installPath">Root installation directory.</param>
    /// <returns><c>true</c> when the process started successfully.</returns>
    public bool Launch(string executablePath, string sessionToken, string installPath)
    {
        if (!File.Exists(executablePath))
            return false;

        var startInfo = new ProcessStartInfo
        {
            FileName = executablePath,
            Arguments = $"--session-token {sessionToken} --install-path \"{installPath}\"",
            UseShellExecute = false,
            WorkingDirectory = installPath,
        };

        _process = new Process { StartInfo = startInfo, EnableRaisingEvents = true };
        _process.Exited += (_, _) => GameExited?.Invoke(this, EventArgs.Empty);
        return _process.Start();
    }

    /// <summary>
    /// Returns true when the game process is running.
    /// </summary>
    public bool IsRunning => _process is not null && !_process.HasExited;

    /// <summary>
    /// Forcefully terminates the game process if running.
    /// </summary>
    public void Terminate()
    {
        if (_process is not null && !_process.HasExited)
            _process.Kill(entireProcessTree: true);
    }
}
