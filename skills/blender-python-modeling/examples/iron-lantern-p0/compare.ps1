param([Parameter(Mandatory)][string]$OutputDirectory, [switch]$FeatureReview)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$out = (Resolve-Path -LiteralPath $OutputDirectory).Path
$font = [Drawing.Font]::new('Segoe UI', 16, [Drawing.FontStyle]::Bold)
$ink = [Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(231, 238, 245))
$tile = [Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(25, 33, 43))

function Add-Tile($graphics, $path, $source, $destination, $label) {
    $image = [Drawing.Image]::FromFile((Join-Path $out $path))
    try {
        if ($null -eq $source) {
            $source = [Drawing.Rectangle]::new(0, 0, $image.Width, $image.Height)
        }
        $graphics.FillRectangle($tile, $destination)
        $graphics.DrawImage($image, $destination, $source, [Drawing.GraphicsUnit]::Pixel)
        $graphics.DrawString($label, $font, $ink, [single]$destination.X, [single]($destination.Y - 30))
    } finally {
        $image.Dispose()
    }
}

function New-Sheet($name, $columns, $rows, $size, $tiles) {
    $width, $height = $size
    $canvas = [Drawing.Bitmap]::new(16 + $columns * ($width + 16), 16 + $rows * ($height + 49))
    $graphics = [Drawing.Graphics]::FromImage($canvas)
    try {
        $graphics.Clear([Drawing.Color]::FromArgb(14, 19, 26))
        $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.TextRenderingHint = [Drawing.Text.TextRenderingHint]::AntiAliasGridFit
        for ($i = 0; $i -lt $tiles.Count; $i++) {
            $item = $tiles[$i]
            $x = 16 + ($i % $columns) * ($width + 16)
            $y = 48 + [Math]::Floor($i / $columns) * ($height + 49)
            $dest = [Drawing.Rectangle]::new($x, $y, $width, $height)
            Add-Tile $graphics $item.Path $item.Source $dest $item.Label
        }
        $canvas.Save((Join-Path $out $name), [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $canvas.Dispose()
    }
}

try {
    if ($FeatureReview) {
        $groups = [ordered]@{'reservoir-width' = 'Base'; 'vent-opening' = 'Vent'; 'hood-seat' = 'Joint'}
        $views = [ordered]@{'reference' = 'reference'; 'before-clay' = 'clay before'; 'after-clay' = 'clay after';
                            'before-material' = 'material before'; 'after-material' = 'material after'}
        $features = foreach ($group in $groups.Keys) {
            foreach ($view in $views.Keys) {
                @{Path="$group/$view.png"; Label="$($groups[$group]) / $($views[$view])"}
            }
        }
        New-Sheet 'comparison-features.png' 5 3 @(248, 248) $features
        return
    }
    $silhouettes = foreach ($view in 'front', 'right') {
        foreach ($tag in 'reference', 'before', 'after') {
            @{Path="$tag-$view.png"; Source=[Drawing.Rectangle]::new(189, 27, 342, 666); Label="$view / $tag"}
        }
    }
    New-Sheet 'comparison-silhouettes.png' 3 2 @(210, 409) $silhouettes
    $details = foreach ($feature in 'vent', 'joint') {
        foreach ($tag in 'before', 'after') {
            @{Path="$tag-$feature.png"; Source=[Drawing.Rectangle]::new(0, 73, 480, 334); Label="$feature / $tag"}
        }
    }
    New-Sheet 'comparison-details.png' 2 2 @(365, 254) $details
} finally {
    $font.Dispose()
    $ink.Dispose()
    $tile.Dispose()
}
