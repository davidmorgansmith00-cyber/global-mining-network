using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace GlobalMiningNetwork.Launcher;

/// <summary>
/// Possible states of the update process.
/// </summary>
public enum UpdateState
{
    Idle,
    Checking,
    Downloading,
    Verifying,
    Applying,
    Ready,
    Error,
}

/// <summary>
/// Download progress snapshot written to progress.json during segmented download.
/// </summary>
public sealed class DownloadProgress
{
    [JsonPropertyName("version")] public string Version { get; set; } = string.Empty;
    [JsonPropertyName("total_bytes")] public long TotalBytes { get; set; }
    [JsonPropertyName("downloaded_bytes")] public long DownloadedBytes { get; set; }
    [JsonPropertyName("completed")] public bool Completed { get; set; }
}

/// <summary>
/// Handles checking for updates, downloading in 1 MB chunks, verifying checksums,
/// applying the update and rolling back to the previous version on failure.
/// </summary>
public sealed class Updater
{
    private const int ChunkSize = 1 * 1024 * 1024; // 1 MB
    private static readonly int[] BackoffSeconds = { 1, 2, 4, 8, 16, 30 };
    private static readonly JsonSerializerOptions JsonOptions =
        new() { WriteIndented = true, PropertyNameCaseInsensitive = true };

    private readonly HttpClient _http;
    private readonly ConfigManager _configManager;

    public UpdateState State { get; private set; } = UpdateState.Idle;
    public event EventHandler<double>? ProgressChanged;

    public Updater(HttpClient http, ConfigManager configManager)
    {
        _http = http;
        _configManager = configManager;
    }

    // ─── Public API ─────────────────────────────────────────────────────────

    /// <summary>
    /// Checks the update manifest. Returns true when a newer version is available.
    /// </summary>
    public async Task<PatchManifestJson?> CheckForUpdateAsync(ReleaseChannel channel,
        CancellationToken ct = default)
    {
        State = UpdateState.Checking;
        string url = $"{ChannelManager.GetChannelUrl(channel)}/manifest.json";
        try
        {
            string json = await RetryAsync(() => _http.GetStringAsync(url, ct));
            var manifest = JsonSerializer.Deserialize<PatchManifestJson>(json, JsonOptions);
            if (manifest is null) { State = UpdateState.Idle; return null; }

            var config = _configManager.Load();
            if (manifest.Version == config.CurrentVersion) { State = UpdateState.Ready; return null; }

            State = UpdateState.Idle;
            return manifest;
        }
        catch
        {
            State = UpdateState.Error;
            return null;
        }
    }

    /// <summary>
    /// Downloads the update in 1 MB chunks and writes progress to progress.json.
    /// </summary>
    public async Task<string?> DownloadUpdateAsync(PatchManifestJson manifest,
        string downloadDir, CancellationToken ct = default)
    {
        State = UpdateState.Downloading;
        Directory.CreateDirectory(downloadDir);
        string progressPath = Path.Combine(downloadDir, "progress.json");

        try
        {
            long totalBytes = manifest.Files.Sum(f => f.SizeBytes);
            long downloadedBytes = 0;
            var allChunks = new List<byte>();

            foreach (var file in manifest.Files)
            {
                string fileUrl = file.DeltaFromVersion is not null
                    ? $"{ChannelManager.GetChannelUrl(ReleaseChannel.Stable)}/deltas/{file.Path}"
                    : $"{ChannelManager.GetChannelUrl(ReleaseChannel.Stable)}/files/{file.Path}";

                byte[] fileBytes = await RetryAsync(() => _http.GetByteArrayAsync(fileUrl, ct));

                // Write in 1 MB chunks to simulate segmented download
                for (int offset = 0; offset < fileBytes.Length; offset += ChunkSize)
                {
                    int len = Math.Min(ChunkSize, fileBytes.Length - offset);
                    allChunks.AddRange(fileBytes[offset..(offset + len)]);
                    downloadedBytes += len;

                    var progress = new DownloadProgress
                    {
                        Version = manifest.Version,
                        TotalBytes = totalBytes,
                        DownloadedBytes = downloadedBytes,
                        Completed = false,
                    };
                    File.WriteAllText(progressPath, JsonSerializer.Serialize(progress, JsonOptions));
                    ProgressChanged?.Invoke(this, totalBytes > 0 ? (double)downloadedBytes / totalBytes * 100 : 0);
                }

                string outPath = Path.Combine(downloadDir, Path.GetFileName(file.Path));
                File.WriteAllBytes(outPath, fileBytes);
            }

            var finalProgress = new DownloadProgress
            {
                Version = manifest.Version,
                TotalBytes = totalBytes,
                DownloadedBytes = downloadedBytes,
                Completed = true,
            };
            File.WriteAllText(progressPath, JsonSerializer.Serialize(finalProgress, JsonOptions));
            State = UpdateState.Idle;
            return downloadDir;
        }
        catch
        {
            State = UpdateState.Error;
            return null;
        }
    }

    /// <summary>
    /// Verifies SHA-256 checksums of all downloaded files against the manifest.
    /// </summary>
    public bool VerifyUpdate(PatchManifestJson manifest, string downloadDir)
    {
        State = UpdateState.Verifying;
        try
        {
            foreach (var file in manifest.Files)
            {
                string outPath = Path.Combine(downloadDir, Path.GetFileName(file.Path));
                if (!File.Exists(outPath)) { State = UpdateState.Error; return false; }

                string actualHash = ComputeSha256(outPath);
                string expectedHash = file.DeltaFromVersion is not null
                    ? file.DeltaSha256 ?? file.Sha256
                    : file.Sha256;

                if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
                {
                    State = UpdateState.Error;
                    return false;
                }
            }
            State = UpdateState.Ready;
            return true;
        }
        catch
        {
            State = UpdateState.Error;
            return false;
        }
    }

    /// <summary>
    /// Applies the downloaded update, backing up the current version first.
    /// </summary>
    public bool ApplyUpdate(PatchManifestJson manifest, string downloadDir, string installPath)
    {
        State = UpdateState.Applying;
        try
        {
            // Back up current version
            string backupDir = Path.Combine(installPath, ".backup");
            Directory.CreateDirectory(backupDir);
            foreach (var file in manifest.Files)
            {
                string current = Path.Combine(installPath, file.Path);
                if (File.Exists(current))
                    File.Copy(current, Path.Combine(backupDir, Path.GetFileName(file.Path)), overwrite: true);
            }

            // Apply new files
            foreach (var file in manifest.Files)
            {
                string src = Path.Combine(downloadDir, Path.GetFileName(file.Path));
                string dst = Path.Combine(installPath, file.Path);
                Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                File.Copy(src, dst, overwrite: true);
            }

            var config = _configManager.Load();
            config.LastVersion = config.CurrentVersion;
            config.CurrentVersion = manifest.Version;
            _configManager.Save(config);

            State = UpdateState.Ready;
            return true;
        }
        catch
        {
            State = UpdateState.Error;
            return false;
        }
    }

    /// <summary>
    /// Rolls back to the previous version using the .backup directory.
    /// </summary>
    public bool Rollback(string installPath)
    {
        try
        {
            string backupDir = Path.Combine(installPath, ".backup");
            if (!Directory.Exists(backupDir)) return false;

            foreach (string src in Directory.GetFiles(backupDir))
                File.Copy(src, Path.Combine(installPath, Path.GetFileName(src)), overwrite: true);

            var config = _configManager.Load();
            config.CurrentVersion = config.LastVersion;
            _configManager.Save(config);

            State = UpdateState.Idle;
            return true;
        }
        catch
        {
            State = UpdateState.Error;
            return false;
        }
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────

    private static string ComputeSha256(string path)
    {
        using var sha = SHA256.Create();
        using var fs = File.OpenRead(path);
        byte[] hash = sha.ComputeHash(fs);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static async Task<T> RetryAsync<T>(Func<Task<T>> action)
    {
        for (int i = 0; i < BackoffSeconds.Length; i++)
        {
            try { return await action(); }
            catch when (i < BackoffSeconds.Length - 1)
            {
                await Task.Delay(BackoffSeconds[i] * 1000);
            }
        }
        return await action(); // final attempt — let it throw
    }
}

/// <summary>Patch manifest as returned by the CDN (mirrors Python PatchManifest dataclass).</summary>
public sealed class PatchManifestJson
{
    [JsonPropertyName("version")] public string Version { get; set; } = string.Empty;
    [JsonPropertyName("release_date")] public string ReleaseDate { get; set; } = string.Empty;
    [JsonPropertyName("channel")] public string Channel { get; set; } = string.Empty;
    [JsonPropertyName("files")] public List<PatchFileJson> Files { get; set; } = [];
    [JsonPropertyName("signature")] public string? Signature { get; set; }
}

/// <summary>File entry in the patch manifest.</summary>
public sealed class PatchFileJson
{
    [JsonPropertyName("path")] public string Path { get; set; } = string.Empty;
    [JsonPropertyName("sha256")] public string Sha256 { get; set; } = string.Empty;
    [JsonPropertyName("size_bytes")] public long SizeBytes { get; set; }
    [JsonPropertyName("delta_from_version")] public string? DeltaFromVersion { get; set; }
    [JsonPropertyName("delta_sha256")] public string? DeltaSha256 { get; set; }
    [JsonPropertyName("delta_size_bytes")] public long? DeltaSizeBytes { get; set; }
}
