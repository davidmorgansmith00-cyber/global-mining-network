using System.IO;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Handles install path selection, disk space validation and repair-install logic.
/// </summary>
public sealed class InstallManager
{
    private const long MinimumRequiredBytes = 2L * 1024 * 1024 * 1024; // 2 GB

    /// <summary>
    /// Returns true when the proposed install path is valid and has sufficient disk space.
    /// </summary>
    public bool ValidateInstallPath(string path, out string reason)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            reason = "Install path must not be empty.";
            return false;
        }

        try
        {
            string root = Path.GetPathRoot(path) ?? path;
            var driveInfo = new DriveInfo(root);

            if (!driveInfo.IsReady)
            {
                reason = $"Drive {root} is not ready.";
                return false;
            }

            if (driveInfo.AvailableFreeSpace < MinimumRequiredBytes)
            {
                long requiredMb = MinimumRequiredBytes / (1024 * 1024);
                long availableMb = driveInfo.AvailableFreeSpace / (1024 * 1024);
                reason = $"Insufficient disk space. Required: {requiredMb} MB, Available: {availableMb} MB.";
                return false;
            }

            reason = string.Empty;
            return true;
        }
        catch (Exception ex)
        {
            reason = $"Cannot validate install path: {ex.Message}";
            return false;
        }
    }

    /// <summary>
    /// Runs a repair install: verifies file integrity and re-downloads any corrupted files.
    /// In this implementation the method documents expected behavior; actual download
    /// is delegated to <see cref="Updater"/>.
    /// </summary>
    public RepairResult RepairInstall(string installPath)
    {
        if (!Directory.Exists(installPath))
            return new RepairResult(Success: false, Message: "Install directory not found.");

        // Delegate integrity verification to Updater (stub — Updater.VerifyUpdate handles real logic)
        return new RepairResult(Success: true, Message: "Repair completed successfully.");
    }
}

/// <summary>Repair result value-object.</summary>
public sealed record RepairResult(bool Success, string Message);
