# Meshtastic Map Tiles Generator

Generate offline map tiles for your Meshtastic T-Deck device! This tool downloads map tiles from various sources and organizes them in the format that Meshtastic expects for offline mapping.

## 🚀 Quick Start

1. **Install dependencies:**
```bash
pip install pillow requests
```

2. **Generate tiles for your city:**
```bash
python meshtastic_tiles.py --city "San Francisco" --min-zoom 8 --max-zoom 12
```

3. **Copy the `tiles` folder to your T-Deck's SD card**

4. **Configure Meshtastic to use offline tiles**

## 📋 Features

- **🏙️ City-based generation**: Just specify city names, no coordinate lookup needed
- **🗺️ Multiple map sources**: OpenStreetMap, satellite imagery, terrain, cycle maps
- **⚡ Fast downloads**: Multi-threaded downloading with rate limiting
- **📦 Smart bounding boxes**: Automatically calculates optimal coverage areas
- **💾 Resume support**: Skips already downloaded tiles
- **🎯 T-Deck optimized**: Default settings perfect for T-Deck storage and screen

## 🎯 Usage Methods

### Method 1: Single City (Recommended for beginners)

Generate tiles around a specific city:

```bash
# Basic city with 20km buffer (default)
python meshtastic_tiles.py --city "Denver" --min-zoom 8 --max-zoom 12

# City with custom buffer
python meshtastic_tiles.py --city "Portland, Oregon" --buffer 50 --min-zoom 8 --max-zoom 12

# High detail for local area
python meshtastic_tiles.py --city "Austin" --buffer 30 --min-zoom 10 --max-zoom 14
```

### Method 2: Multiple Cities

Create optimal coverage for multiple cities (great for road trips):

```bash
# Bay Area coverage
python meshtastic_tiles.py --cities "San Francisco; Oakland; San Jose" --min-zoom 8 --max-zoom 12

# Road trip route
python meshtastic_tiles.py --cities "Los Angeles; Bakersfield; Fresno; Modesto; Sacramento; San Francisco" --min-zoom 8 --max-zoom 11

# Regional coverage with larger buffer
python meshtastic_tiles.py --cities "Seattle; Tacoma; Olympia" --buffer 40 --min-zoom 8 --max-zoom 12
```

### Method 3: Predefined Regions

Use built-in regional boundaries:

```bash
# Entire states
python meshtastic_tiles.py --region california --min-zoom 6 --max-zoom 10
python meshtastic_tiles.py --region texas --min-zoom 6 --max-zoom 10

# Countries/continents
python meshtastic_tiles.py --region usa --min-zoom 4 --max-zoom 8
python meshtastic_tiles.py --region north_america --min-zoom 4 --max-zoom 8
```

**Available regions:** `north_america`, `usa`, `canada`, `mexico`, `california`, `texas`, `alaska`

### Method 4: Custom Coordinates

Specify exact boundaries:

```bash
python meshtastic_tiles.py --coords --north 40.8 --south 40.6 --east -74.0 --west -74.2 --min-zoom 10 --max-zoom 14
```

## 🗺️ Map Sources

Choose different map types with the `--source` option:

```bash
# Standard street map (default)
python meshtastic_tiles.py --city "Denver" --source osm

# Satellite imagery
python meshtastic_tiles.py --city "Denver" --source satellite

# Topographic/terrain
python meshtastic_tiles.py --city "Denver" --source terrain

# Cycling-focused
python meshtastic_tiles.py --city "Denver" --source cycle
```

## 🔍 Zoom Levels Guide

Choose zoom levels based on your needs and storage capacity:

| Zoom Range | Use Case | Coverage | Storage (per city) |
|------------|----------|----------|-------------------|
| 4-8 | Continental navigation | Very wide area | 10-50 MB |
| 8-12 | **Recommended for T-Deck** | Regional detail | 50-200 MB |
| 10-14 | Local/urban navigation | Street-level | 100-500 MB |
| 12-16 | High detail | Building-level | 500+ MB |

### Recommended Zoom Strategies:

**Storage Conscious (16GB SD):**
```bash
python meshtastic_tiles.py --city "Your City" --min-zoom 8 --max-zoom 11
```

**Balanced (32GB SD):**
```bash
python meshtastic_tiles.py --city "Your City" --min-zoom 8 --max-zoom 12
```

**High Detail (64GB+ SD):**
```bash
python meshtastic_tiles.py --city "Your City" --min-zoom 8 --max-zoom 14
```

## 📱 Real-World Examples

### Hiking/Camping Trip
```bash
# Download terrain maps for Yosemite area
python meshtastic_tiles.py --cities "Yosemite Valley; Mammoth Lakes; Bishop" --source terrain --min-zoom 10 --max-zoom 14
```

### Urban Mesh Network
```bash
# High-detail city coverage
python meshtastic_tiles.py --city "Portland, Oregon" --buffer 25 --min-zoom 10 --max-zoom 13
```

### Cross-Country Road Trip
```bash
# Wide coverage at lower detail
python meshtastic_tiles.py --cities "New York; Philadelphia; Washington DC; Richmond; Raleigh; Atlanta; Birmingham; New Orleans; Houston; Austin; San Antonio" --min-zoom 8 --max-zoom 11
```

### Regional Emergency Preparedness
```bash
# State-wide coverage
python meshtastic_tiles.py --region california --min-zoom 6 --max-zoom 10
```

### Local Mesh Testing
```bash
# Detailed local area
python meshtastic_tiles.py --city "Your City" --buffer 15 --min-zoom 10 --max-zoom 13
```

## ⚙️ Advanced Options

### Performance Tuning
```bash
# Faster downloads (be respectful to servers)
python meshtastic_tiles.py --city "Denver" --max-workers 6 --delay 0.1

# Slower, more conservative
python meshtastic_tiles.py --city "Denver" --max-workers 2 --delay 0.5
```

### Custom Output Directory
```bash
python meshtastic_tiles.py --city "Denver" --output-dir "my_tiles"
```

### Generate Test Tile
```bash
python meshtastic_tiles.py --sample-only
```

## 💾 Storage Estimates

**Single City Examples (20km buffer):**
- San Francisco (zoom 8-12): ~150 MB
- Denver (zoom 8-12): ~120 MB  
- New York (zoom 8-12): ~180 MB

**Multiple Cities:**
- Bay Area (SF, Oakland, San Jose) zoom 8-12: ~400 MB
- I-5 Corridor (LA to SF) zoom 8-11: ~800 MB

**Regional:**
- California zoom 6-10: ~2-5 GB
- USA zoom 4-8: ~500 MB - 2 GB

## 🔧 T-Deck Integration

1. **Generate tiles** using this script
2. **Create Directory on SD Card** maps/oms
3. **Copy all the folders** from inside tiles to /maps/oms on your SD card.
It should look like this:
```
/maps/oms/0/
/maps/oms/1/
/maps/oms/3/
...
```

## ⚠️ Important Notes

- **Be respectful** to tile servers - the script includes delays between requests
- **Check storage space** before generating large areas
- **Start small** - test with a single city first
- **Higher zoom = more storage** - each zoom level roughly 4x more tiles
- **Satellite imagery** takes more storage than street maps

## 🐛 Troubleshooting

**"No tiles downloaded":**
- Check your internet connection
- Verify city name spelling
- Try adding state/country: `"Portland, Oregon"`

**"Permission denied" errors:**
- Make sure you have write permissions to the output directory
- Try running with `sudo` if necessary

**Very slow downloads:**
- Reduce `--max-workers` to 2-3
- Increase `--delay` to 0.3-0.5
- Check if your ISP is throttling requests

**Out of storage:**
- Reduce zoom range (try 8-11 instead of 8-14)
- Use smaller buffer around cities
- Generate tiles for smaller areas

## 🤝 Contributing

Found a bug or want to add features? Contributions welcome!

Common improvements needed:
- Additional map sources
- Better error handling
- Progress bars
- Tile format conversion
- Batch processing scripts

## 📄 License

This tool is for personal/educational use. Please respect the terms of service of map tile providers:
- OpenStreetMap: [Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)
- Other sources: Check their individual terms

Happy mapping! 🗺️📡
