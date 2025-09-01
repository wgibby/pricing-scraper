#!/usr/bin/env python3
"""
File Organization Cleanup Script
Moves scattered Disney+ files to the proper date-organized structure
"""
import os
import shutil
import glob
from datetime import datetime

def cleanup_scattered_files():
    """Move scattered files to proper organization."""
    
    print("🧹 CLEANING UP SCATTERED FILES")
    print("=" * 40)
    
    # Create target directory structure
    today = datetime.now().strftime("%Y-%m-%d")
    target_base = os.path.join('screenshots', today)
    
    target_dirs = {
        'screenshots': target_base,
        'html': os.path.join(target_base, 'html'),
        'logs': os.path.join(target_base, 'logs'),
        'results': target_base  # Results go in the main date folder
    }
    
    # Create directories
    for dir_path in target_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
        print(f"📁 Created: {dir_path}")
    
    # Files to move (patterns in root directory)
    file_patterns = {
        'debug': {
            'pattern': 'debug_disney*.png',
            'target': target_dirs['screenshots'],
            'description': 'Debug screenshots'
        },
        'results': {
            'pattern': 'disney+_*_result.json',
            'target': target_dirs['results'], 
            'description': 'Result JSON files'
        },
        'screenshots': {
            'pattern': 'disney+_*.png',
            'target': target_dirs['screenshots'],
            'description': 'Disney+ screenshots'
        },
        'html': {
            'pattern': 'disney+_*.html',
            'target': target_dirs['html'],
            'description': 'HTML files'
        }
    }
    
    total_moved = 0
    
    for category, info in file_patterns.items():
        print(f"\n🔍 Looking for {info['description']}...")
        
        matching_files = glob.glob(info['pattern'])
        
        if matching_files:
            print(f"  Found {len(matching_files)} files:")
            
            for file_path in matching_files:
                filename = os.path.basename(file_path)
                target_path = os.path.join(info['target'], filename)
                
                try:
                    shutil.move(file_path, target_path)
                    print(f"  ✅ {filename} → {info['target']}")
                    total_moved += 1
                except Exception as e:
                    print(f"  ❌ Error moving {filename}: {e}")
        else:
            print(f"  📝 No {info['description']} found")
    
    # Check for any other scattered files
    other_patterns = [
        '*.png', '*.json', '*.html', '*.log'
    ]
    
    suspicious_files = []
    for pattern in other_patterns:
        files = glob.glob(pattern)
        for file in files:
            # Skip if it's not a scraper output file
            if any(keyword in file.lower() for keyword in ['disney', 'netflix', 'spotify', 'debug', 'result']):
                suspicious_files.append(file)
    
    if suspicious_files:
        print(f"\n⚠️  Found {len(suspicious_files)} other potentially scattered files:")
        for file in suspicious_files[:10]:  # Show first 10
            print(f"  📄 {file}")
        if len(suspicious_files) > 10:
            print(f"  ... and {len(suspicious_files) - 10} more")
        
        move_others = input(f"\nMove these files to {target_base}? (y/n): ").lower().strip()
        if move_others == 'y':
            for file in suspicious_files:
                try:
                    target = os.path.join(target_base, os.path.basename(file))
                    shutil.move(file, target)
                    print(f"  ✅ Moved {file}")
                    total_moved += 1
                except Exception as e:
                    print(f"  ❌ Error moving {file}: {e}")
    
    print(f"\n{'='*40}")
    print(f"✅ CLEANUP COMPLETE")
    print(f"📊 Total files moved: {total_moved}")
    print(f"📁 Files organized in: {target_base}")
    print(f"{'='*40}")
    
    return total_moved

def update_disney_handler():
    """Update Disney+ handler to prevent future scattered files."""
    
    handler_path = 'site_handlers/disney.py'
    
    if not os.path.exists(handler_path):
        print(f"⚠️ {handler_path} not found - skipping handler update")
        return False
    
    print(f"\n🔧 UPDATING DISNEY+ HANDLER")
    print("=" * 40)
    
    try:
        # Read current handler
        with open(handler_path, 'r') as f:
            content = f.read()
        
        # Check if clean_up method needs updating
        if 'debug_disney_final_' in content:
            print("📝 Found debug screenshot code in clean_up method")
            
            # Replace the problematic debug screenshot line
            old_debug_line = 'debug_path = f"debug_disney_final_{int(time.time())}.png"'
            new_debug_comment = '# Debug screenshots now handled by main scraper - no need for separate debug files'
            
            if old_debug_line in content:
                content = content.replace(old_debug_line, new_debug_comment)
                
                # Also comment out the screenshot line
                old_screenshot_line = 'page.screenshot(path=debug_path, full_page=True)'
                new_screenshot_comment = '# page.screenshot(path=debug_path, full_page=True)  # Disabled to prevent scattered files'
                content = content.replace(old_screenshot_line, new_screenshot_comment)
                
                # Write updated handler
                with open(handler_path, 'w') as f:
                    f.write(content)
                
                print("✅ Updated Disney+ handler to prevent scattered debug files")
                return True
            else:
                print("📝 Handler already appears to be updated")
                return True
        else:
            print("✅ Disney+ handler looks good - no scattered file issues found")
            return True
            
    except Exception as e:
        print(f"❌ Error updating handler: {e}")
        return False

def main():
    """Run the complete file organization cleanup."""
    
    print("🏰 DISNEY+ FILE ORGANIZATION CLEANUP")
    print("=" * 50)
    print("This script will:")
    print("1. Move scattered Disney+ files to date-organized folders")
    print("2. Update the Disney+ handler to prevent future issues")
    print("3. Ensure consistent file organization")
    print()
    
    # Step 1: Clean up existing files
    moved_count = cleanup_scattered_files()
    
    # Step 2: Update handler
    handler_updated = update_disney_handler()
    
    # Final summary
    print(f"\n🎯 SUMMARY:")
    print(f"📦 Files moved: {moved_count}")
    print(f"🔧 Handler updated: {'✅' if handler_updated else '❌'}")
    print(f"\n💡 NEXT STEPS:")
    print(f"1. All Disney+ files should now be in screenshots/{datetime.now().strftime('%Y-%m-%d')}/")
    print(f"2. Future scraping will maintain this organization")
    print(f"3. Run your scraper normally: python modified_scraper.py --website Disney+ --country [country]")

if __name__ == "__main__":
    main()