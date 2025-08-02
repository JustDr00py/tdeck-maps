#!/usr/bin/env python3
"""
Meshtastic Map Tile Generator for T-Deck
Generates map tiles from various sources for offline use
"""

import os
import sys
import math
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import argparse
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

class CityLookup:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MeshtasticTileGenerator/1.0'
        })
    
    def get_coordinates(self, city, state=None, country=None):
        """Get coordinates using OpenStreetMap Nominatim (free)"""
        base_url = "https://nominatim.openstreetmap.org/search"
        
        # Build query
        query = city
        if state:
            query += f", {state}"
        if country:
            query += f", {country}"
        
        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            result = data[0]
            return {
                'name': result.get('display_name', 'Unknown'),
                'lat': float(result['lat']),
                'lon': float(result['lon']),
                'south': float(result['boundingbox'][0]),
                'north': float(result['boundingbox'][1]),
                'west': float(result['boundingbox'][2]),
                'east': float(result['boundingbox'][3]),
                'type': result.get('type', 'unknown')
            }
            
        except Exception as e:
            print(f"Error looking up coordinates for {query}: {e}")
            return None
    
    def get_bounding_box_for_cities(self, cities, buffer_km=10):
        """Get bounding box for multiple cities with buffer in kilometers"""
        all_coords = []
        
        print(f"Looking up coordinates for {len(cities)} cities...")
        for city_info in cities:
            if isinstance(city_info, str):
                city, state, country = city_info, None, None
            else:
                city = city_info.get('city')
                state = city_info.get('state')
                country = city_info.get('country')
            
            result = self.get_coordinates(city, state, country)
            if result:
                all_coords.append(result)
                print(f"✓ {city}: {result['lat']:.4f}, {result['lon']:.4f}")
            else:
                print(f"✗ {city}: Not found")
        
        if not all_coords:
            print("No valid coordinates found")
            return None
        
        # Calculate bounding box
        norths = [c['north'] for c in all_coords]
        souths = [c['south'] for c in all_coords]
        easts = [c['east'] for c in all_coords]
        wests = [c['west'] for c in all_coords]
        
        # Convert km buffer to degrees (approximate)
        buffer_deg = buffer_km / 111.0  # ~111km per degree
        
        north = max(norths) + buffer_deg
        south = min(souths) - buffer_deg
        east = max(easts) + buffer_deg
        west = min(wests) - buffer_deg
        
        print(f"\n📦 Bounding box for {len(all_coords)} cities (±{buffer_km}km buffer):")
        print(f"   North: {north:.4f}")
        print(f"   South: {south:.4f}")
        print(f"   East:  {east:.4f}")
        print(f"   West:  {west:.4f}")
        
        return {
            'north': north,
            'south': south,
            'east': east,
            'west': west,
            'cities': all_coords
        }

class MeshtasticTileGenerator:
    def __init__(self, output_dir="tiles", tile_size=256, delay=0.1):
        self.output_dir = Path(output_dir)
        self.tile_size = tile_size
        self.delay = delay  # Delay between requests to be respectful
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MeshtasticTileGenerator/1.0'
        })
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
    def deg2num(self, lat_deg, lon_deg, zoom):
        """Convert lat/lon to tile numbers"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def num2deg(self, x, y, zoom):
        """Convert tile numbers to lat/lon"""
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def get_tile_url(self, x, y, zoom, source="osm"):
        """Get tile URL for different map sources"""
        sources = {
            "osm": f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png",
            "satellite": f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{y}/{x}",
            "terrain": f"https://tile.opentopomap.org/{zoom}/{x}/{y}.png",
            "cycle": f"https://tile.thunderforest.com/cycle/{zoom}/{x}/{y}.png"
        }
        return sources.get(source, sources["osm"])
    
    def download_tile(self, x, y, zoom, source="osm"):
        """Download a single tile"""
        url = self.get_tile_url(x, y, zoom, source)
        
        # Create directory structure
        tile_dir = self.output_dir / str(zoom) / str(x)
        tile_dir.mkdir(parents=True, exist_ok=True)
        
        tile_path = tile_dir / f"{y}.png"
        
        # Skip if tile already exists
        if tile_path.exists():
            return tile_path, True
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Save the tile
            with open(tile_path, 'wb') as f:
                f.write(response.content)
            
            time.sleep(self.delay)  # Be respectful to tile servers
            return tile_path, True
            
        except Exception as e:
            print(f"Error downloading tile {x},{y},{zoom}: {e}")
            return None, False
    
    def generate_tiles(self, north, south, east, west, min_zoom=8, max_zoom=16, source="osm", max_workers=4):
        """Generate tiles for a bounding box"""
        print(f"Generating tiles for bounds: N:{north}, S:{south}, E:{east}, W:{west}")
        print(f"Zoom levels: {min_zoom} to {max_zoom}")
        print(f"Source: {source}")
        
        # Validate coordinates
        if north <= south:
            print("Error: North latitude must be greater than south latitude")
            return
        if east <= west:
            print("Error: East longitude must be greater than west longitude")
            return
        
        total_tiles = 0
        downloaded_tiles = 0
        
        # Calculate total tiles for progress tracking
        for zoom in range(min_zoom, max_zoom + 1):
            # Calculate tile boundaries correctly
            x_min, y_max = self.deg2num(south, west, zoom)  # Bottom-left
            x_max, y_min = self.deg2num(north, east, zoom)  # Top-right
            
            # Ensure proper ordering
            if x_min > x_max:
                x_min, x_max = x_max, x_min
            if y_min > y_max:
                y_min, y_max = y_max, y_min
            
            tiles_this_zoom = (x_max - x_min + 1) * (y_max - y_min + 1)
            total_tiles += tiles_this_zoom
            print(f"Zoom {zoom}: {tiles_this_zoom} tiles (x:{x_min}-{x_max}, y:{y_min}-{y_max})")
        
        print(f"Total tiles to process: {total_tiles}")
        
        if total_tiles == 0:
            print("No tiles to download. Check your coordinates.")
            return
        
        # Download tiles with threading
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for zoom in range(min_zoom, max_zoom + 1):
                # Calculate tile boundaries correctly
                x_min, y_max = self.deg2num(south, west, zoom)  # Bottom-left
                x_max, y_min = self.deg2num(north, east, zoom)  # Top-right
                
                # Ensure proper ordering
                if x_min > x_max:
                    x_min, x_max = x_max, x_min
                if y_min > y_max:
                    y_min, y_max = y_max, y_min
                
                print(f"Processing zoom level {zoom} (x:{x_min}-{x_max}, y:{y_min}-{y_max})...")
                
                for x in range(x_min, x_max + 1):
                    for y in range(y_min, y_max + 1):
                        future = executor.submit(self.download_tile, x, y, zoom, source)
                        futures.append(future)
            
            # Process completed downloads
            for future in as_completed(futures):
                tile_path, success = future.result()
                if success:
                    downloaded_tiles += 1
                
                if downloaded_tiles % 100 == 0:
                    print(f"Downloaded {downloaded_tiles}/{total_tiles} tiles")
        
        print(f"Completed! Downloaded {downloaded_tiles}/{total_tiles} tiles")
        
        # Generate metadata
        self.generate_metadata(north, south, east, west, min_zoom, max_zoom, source)
    
    def generate_metadata(self, north, south, east, west, min_zoom, max_zoom, source):
        """Generate metadata file for Meshtastic"""
        metadata = {
            "name": f"Generated tiles ({source})",
            "description": f"Map tiles for Meshtastic T-Deck",
            "bounds": [west, south, east, north],
            "minzoom": min_zoom,
            "maxzoom": max_zoom,
            "format": "png",
            "type": "baselayer",
            "source": source,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Metadata saved to: {metadata_path}")
    
    def create_sample_tile(self, text="Sample Tile"):
        """Create a sample tile for testing"""
        img = Image.new('RGB', (self.tile_size, self.tile_size), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Draw text in center
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (self.tile_size - text_width) // 2
        y = (self.tile_size - text_height) // 2
        
        draw.text((x, y), text, fill='black', font=font)
        
        # Save sample tile
        sample_dir = self.output_dir / "sample"
        sample_dir.mkdir(exist_ok=True)
        img.save(sample_dir / "sample.png")
        print(f"Sample tile saved to: {sample_dir / 'sample.png'}")

def get_region_bounds(region):
    """Get predefined bounds for common regions"""
    regions = {
        'north_america': {
            'north': 83.0,   # Northern Canada/Alaska
            'south': 7.0,    # Southern Mexico/Central America
            'east': -52.0,   # Eastern Canada (Newfoundland)
            'west': -168.0   # Western Alaska
        },
        'usa': {
            'north': 49.0,   # Canadian border
            'south': 24.0,   # Southern Florida/Texas
            'east': -66.0,   # Eastern seaboard
            'west': -125.0   # West coast
        },
        'canada': {
            'north': 83.0,   # Arctic islands
            'south': 41.0,   # Southern Ontario
            'east': -52.0,   # Newfoundland
            'west': -141.0   # Alaska border
        },
        'mexico': {
            'north': 32.7,   # US border
            'south': 14.5,   # Guatemala border
            'east': -86.7,   # Eastern coast
            'west': -117.1   # Western coast
        },
        'california': {
            'north': 42.0,   # Oregon border (correct)
            'south': 32.5,   # Mexico border (should be 32.534 to be exact)
            'east': -114.131, # Nevada/Arizona border (more precise)
            'west': -124.409  # Pacific coast (more precise)
        },
        'texas': {
            'north': 36.5,   # Oklahoma border
            'south': 25.8,   # Mexico border
            'east': -93.5,   # Louisiana border
            'west': -106.6   # New Mexico border
        },
        'alaska': {
            'north': 71.4,   # Arctic Ocean
            'south': 54.4,   # Aleutian Islands
            'east': -129.9,  # Canadian border
            'west': -172.4   # Aleutian Islands
        }
    }
    return regions.get(region.lower())

def main():
    parser = argparse.ArgumentParser(description='Generate map tiles for Meshtastic T-Deck')
    
    # Method selection (mutually exclusive)
    method_group = parser.add_mutually_exclusive_group(required=True)
    method_group.add_argument('--region', type=str, 
                        choices=['north_america', 'usa', 'canada', 'mexico', 'california', 'texas', 'alaska'],
                        help='Predefined region')
    method_group.add_argument('--city', type=str, help='City name (e.g., "San Francisco" or "Portland, Oregon")')
    method_group.add_argument('--cities', type=str, help='Multiple cities separated by semicolons (e.g., "San Francisco; Oakland; San Jose")')
    method_group.add_argument('--coords', action='store_true', help='Use custom coordinates (requires --north, --south, --east, --west)')
    
    # City options
    parser.add_argument('--buffer', type=int, default=20, help='Buffer around city/cities in kilometers (default: 20)')
    
    # Custom coordinates (only used with --coords)
    parser.add_argument('--north', type=float, help='North latitude (required with --coords)')
    parser.add_argument('--south', type=float, help='South latitude (required with --coords)')
    parser.add_argument('--east', type=float, help='East longitude (required with --coords)')
    parser.add_argument('--west', type=float, help='West longitude (required with --coords)')
    
    # Tile generation options
    parser.add_argument('--min-zoom', type=int, default=8, help='Minimum zoom level')
    parser.add_argument('--max-zoom', type=int, default=12, help='Maximum zoom level')
    parser.add_argument('--source', default='osm', choices=['osm', 'satellite', 'terrain', 'cycle'],
                        help='Map source')
    parser.add_argument('--output-dir', default='tiles', help='Output directory')
    parser.add_argument('--delay', type=float, default=0.2, help='Delay between requests (seconds)')
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum concurrent downloads')
    parser.add_argument('--sample-only', action='store_true', help='Generate sample tile only')
    
    args = parser.parse_args()
    
    # Create generator
    generator = MeshtasticTileGenerator(
        output_dir=args.output_dir,
        delay=args.delay
    )
    
    if args.sample_only:
        generator.create_sample_tile()
        return
    
    # Determine coordinates based on method
    north = south = east = west = None
    area_name = "unknown"
    
    if args.region:
        # Use predefined region
        bounds = get_region_bounds(args.region)
        if not bounds:
            print(f"Unknown region: {args.region}")
            return
        north, south, east, west = bounds['north'], bounds['south'], bounds['east'], bounds['west']
        area_name = args.region
        
    elif args.city:
        # Single city lookup
        lookup = CityLookup()
        coord = lookup.get_coordinates(args.city)
        if not coord:
            print(f"Could not find coordinates for: {args.city}")
            return
        
        print(f"Found {args.city}: {coord['lat']:.4f}, {coord['lon']:.4f}")
        
        # Create bounding box around city
        buffer_deg = args.buffer / 111.0  # Convert km to degrees
        north = coord['north'] + buffer_deg
        south = coord['south'] - buffer_deg
        east = coord['east'] + buffer_deg
        west = coord['west'] - buffer_deg
        area_name = args.city
        
    elif args.cities:
        # Multiple cities lookup
        lookup = CityLookup()
        cities = [city.strip() for city in args.cities.split(';')]
        bbox = lookup.get_bounding_box_for_cities(cities, args.buffer)
        if not bbox:
            print("Could not determine bounding box for cities")
            return
        
        north, south, east, west = bbox['north'], bbox['south'], bbox['east'], bbox['west']
        area_name = f"{len(bbox['cities'])} cities"
        
    elif args.coords:
        # Custom coordinates
        if not all([args.north, args.south, args.east, args.west]):
            print("Error: --coords requires --north, --south, --east, --west")
            return
        north, south, east, west = args.north, args.south, args.east, args.west
        area_name = "custom area"
        
    # Validation
    if north is None:
        print("Error: Could not determine coordinates")
        return
    
    # Warning for large areas
    if args.region in ['north_america', 'usa', 'canada']:
        print("⚠️  WARNING: Large region selected!")
        print(f"This will generate a LOT of tiles. Estimated storage for zoom {args.min_zoom}-{args.max_zoom}:")
        
        # Rough estimate with corrected calculation
        total_tiles = 0
        for zoom in range(args.min_zoom, args.max_zoom + 1):
            x_min, y_max = generator.deg2num(south, west, zoom)  # Bottom-left
            x_max, y_min = generator.deg2num(north, east, zoom)  # Top-right
            
            # Ensure proper ordering
            if x_min > x_max:
                x_min, x_max = x_max, x_min
            if y_min > y_max:
                y_min, y_max = y_max, y_min
                
            tiles_this_zoom = (x_max - x_min + 1) * (y_max - y_min + 1)
            total_tiles += tiles_this_zoom
        
        estimated_mb = total_tiles * 15 / 1024  # ~15KB per tile average
        print(f"  - Estimated tiles: {total_tiles:,}")
        print(f"  - Estimated size: {estimated_mb:.1f} MB")
        print("  - Consider starting with lower zoom levels or smaller regions")
        
        confirm = input("Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return
    
    print(f"Generating tiles for: {args.region if args.region else 'custom area'}")
    
    # Generate tiles
    generator.generate_tiles(
        north=north,
        south=south,
        east=east,
        west=west,
        min_zoom=args.min_zoom,
        max_zoom=args.max_zoom,
        source=args.source,
        max_workers=args.max_workers
    )

if __name__ == "__main__":
    main()
