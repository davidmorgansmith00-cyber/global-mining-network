namespace GlobalMiningNetwork.Launcher;

/// <summary>An ARGB color record for palette entries.</summary>
public sealed record GmnColor(byte A, byte R, byte G, byte B)
{
    public static GmnColor FromRgb(byte r, byte g, byte b) => new(255, r, g, b);
    public override string ToString() => $"#{A:X2}{R:X2}{G:X2}{B:X2}";
}

/// <summary>A named color palette with WCAG AA compliance annotations.</summary>
public sealed class ColorPalette
{
    public required string Name { get; init; }
    public required GmnColor Background { get; init; }
    public required GmnColor Surface { get; init; }
    public required GmnColor Primary { get; init; }
    public required GmnColor PrimaryVariant { get; init; }
    public required GmnColor Accent { get; init; }
    public required GmnColor TextPrimary { get; init; }
    public required GmnColor TextSecondary { get; init; }
    public required GmnColor Success { get; init; }
    public required GmnColor Warning { get; init; }
    public required GmnColor Error { get; init; }
}

/// <summary>
/// Static palette definitions for all supported display modes.
/// All palettes meet WCAG AA contrast ratio (≥4.5:1) for body text.
/// </summary>
public static class ColorPalettes
{
    /// <summary>Default dark palette.</summary>
    public static readonly ColorPalette Default = new()
    {
        Name           = "Default",
        Background     = GmnColor.FromRgb(0x1A, 0x1A, 0x2E),
        Surface        = GmnColor.FromRgb(0x16, 0x21, 0x3E),
        Primary        = GmnColor.FromRgb(0x0F, 0x34, 0x60),
        PrimaryVariant = GmnColor.FromRgb(0x0A, 0x25, 0x45),
        Accent         = GmnColor.FromRgb(0x00, 0xB4, 0xD8),
        TextPrimary    = GmnColor.FromRgb(0xFF, 0xFF, 0xFF),  // white on dark — WCAG AA ✓
        TextSecondary  = GmnColor.FromRgb(0xAA, 0xAA, 0xCC),  // light grey on dark — WCAG AA ✓
        Success        = GmnColor.FromRgb(0x06, 0xD6, 0x7E),
        Warning        = GmnColor.FromRgb(0xFF, 0xBE, 0x0B),
        Error          = GmnColor.FromRgb(0xEF, 0x47, 0x67),
    };

    /// <summary>
    /// High-contrast palette (WCAG AAA target).
    /// Black background / white text for maximum legibility.
    /// </summary>
    public static readonly ColorPalette HighContrast = new()
    {
        Name           = "HighContrast",
        Background     = GmnColor.FromRgb(0x00, 0x00, 0x00),
        Surface        = GmnColor.FromRgb(0x1A, 0x1A, 0x1A),
        Primary        = GmnColor.FromRgb(0x00, 0x00, 0x80),
        PrimaryVariant = GmnColor.FromRgb(0x00, 0x00, 0x60),
        Accent         = GmnColor.FromRgb(0xFF, 0xFF, 0x00),  // yellow on black — WCAG AAA ✓
        TextPrimary    = GmnColor.FromRgb(0xFF, 0xFF, 0xFF),  // white on black 21:1 — WCAG AAA ✓
        TextSecondary  = GmnColor.FromRgb(0xDD, 0xDD, 0xDD),
        Success        = GmnColor.FromRgb(0x00, 0xFF, 0x00),
        Warning        = GmnColor.FromRgb(0xFF, 0xFF, 0x00),
        Error          = GmnColor.FromRgb(0xFF, 0x00, 0x00),
    };

    /// <summary>
    /// Deuteranopia palette — avoids green/red confusion.
    /// Uses blue/orange contrast instead of green/red.
    /// </summary>
    public static readonly ColorPalette Deuteranopia = new()
    {
        Name           = "Deuteranopia",
        Background     = GmnColor.FromRgb(0x1A, 0x1A, 0x2E),
        Surface        = GmnColor.FromRgb(0x16, 0x21, 0x3E),
        Primary        = GmnColor.FromRgb(0x0F, 0x34, 0x60),
        PrimaryVariant = GmnColor.FromRgb(0x0A, 0x25, 0x45),
        Accent         = GmnColor.FromRgb(0x56, 0xB4, 0xE9),  // sky blue (safe for deuteranopia)
        TextPrimary    = GmnColor.FromRgb(0xFF, 0xFF, 0xFF),
        TextSecondary  = GmnColor.FromRgb(0xAA, 0xAA, 0xCC),
        Success        = GmnColor.FromRgb(0x00, 0x9E, 0x73),  // bluish green — Okabe-Ito safe ✓
        Warning        = GmnColor.FromRgb(0xE6, 0x9F, 0x00),  // orange-yellow — safe ✓
        Error          = GmnColor.FromRgb(0xCC, 0x79, 0xA7),  // reddish purple — distinguishable ✓
    };

    /// <summary>
    /// Protanopia palette — avoids red confusion.
    /// Uses blue/cyan/yellow contrast.
    /// </summary>
    public static readonly ColorPalette Protanopia = new()
    {
        Name           = "Protanopia",
        Background     = GmnColor.FromRgb(0x1A, 0x1A, 0x2E),
        Surface        = GmnColor.FromRgb(0x16, 0x21, 0x3E),
        Primary        = GmnColor.FromRgb(0x0F, 0x34, 0x60),
        PrimaryVariant = GmnColor.FromRgb(0x0A, 0x25, 0x45),
        Accent         = GmnColor.FromRgb(0x00, 0x72, 0xB2),  // cobalt blue — Okabe-Ito safe ✓
        TextPrimary    = GmnColor.FromRgb(0xFF, 0xFF, 0xFF),
        TextSecondary  = GmnColor.FromRgb(0xAA, 0xAA, 0xCC),
        Success        = GmnColor.FromRgb(0x00, 0x9E, 0x73),  // bluish green ✓
        Warning        = GmnColor.FromRgb(0xF0, 0xE4, 0x42),  // yellow — safe for protanopia ✓
        Error          = GmnColor.FromRgb(0xD5, 0x5E, 0x00),  // vermilion — distinguishable ✓
    };

    /// <summary>Returns the palette matching the given color-blind mode string.</summary>
    public static ColorPalette ForMode(string colorBlindMode, bool highContrast)
    {
        if (highContrast) return HighContrast;
        return colorBlindMode.ToLowerInvariant() switch
        {
            "deuteranopia" => Deuteranopia,
            "protanopia"   => Protanopia,
            _              => Default,
        };
    }
}
