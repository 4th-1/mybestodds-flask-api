#!/usr/bin/env python3
"""
subscriber_id_manager.py

Manages unique subscriber IDs to prevent conflicts.
Implements standardized format: {INITIALS}{###} (e.g., JDS001, AA001)
"""

import json
import re
from pathlib import Path
from typing import Dict, Set, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SubscriberInfo:
    """Subscriber information for ID generation."""
    first_name: str
    last_name: str
    birth_date: str
    current_id: Optional[str] = None

class SubscriberIDManager:
    """Manages unique subscriber IDs and prevents conflicts."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.subscribers_dir = project_root / "data" / "subscribers"
        self.id_registry_file = project_root / "data" / "subscriber_id_registry.json"
        self.id_registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Dict]:
        """Load existing ID registry or create new one."""
        if self.id_registry_file.exists():
            with open(self.id_registry_file, 'r') as f:
                return json.load(f)
        return {
            "used_ids": {},  # id -> {name, birth_date, file_path}
            "initials_counters": {}  # initials -> next_number
        }
    
    def _save_registry(self):
        """Save ID registry to file."""
        self.id_registry_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.id_registry_file, 'w') as f:
            json.dump(self.id_registry, f, indent=2)
    
    def generate_initials(self, first_name: str, last_name: str) -> str:
        """Generate initials from first and last name."""
        # Handle multi-word first names (e.g., "Joseph David" -> "JD")
        first_initial = first_name.strip()[0].upper()
        
        # Handle middle names in last name (e.g., "Smith Jr" -> "SJ") 
        last_parts = last_name.strip().split()
        if len(last_parts) > 1:
            # Use first letter of each part
            last_initials = ''.join(part[0].upper() for part in last_parts[:2])
            return first_initial + last_initials
        else:
            return first_initial + last_name.strip()[0].upper()
    
    def generate_unique_id(self, subscriber_info: SubscriberInfo) -> str:
        """Generate a unique subscriber ID."""
        initials = self.generate_initials(subscriber_info.first_name, subscriber_info.last_name)
        
        # Get next number for these initials
        if initials not in self.id_registry["initials_counters"]:
            self.id_registry["initials_counters"][initials] = 1
        
        counter = self.id_registry["initials_counters"][initials]
        new_id = f"{initials}{counter:03d}"
        
        # Check if ID is already used (shouldn't happen, but safety check)
        while new_id in self.id_registry["used_ids"]:
            counter += 1
            new_id = f"{initials}{counter:03d}"
        
        # Register the new ID
        self.id_registry["used_ids"][new_id] = {
            "name": f"{subscriber_info.first_name} {subscriber_info.last_name}",
            "birth_date": subscriber_info.birth_date,
            "file_path": "",  # Will be set when file is created
            "created_date": "2025-12-22"
        }
        
        # Increment counter for next time
        self.id_registry["initials_counters"][initials] = counter + 1
        
        self._save_registry()
        return new_id
    
    def check_existing_conflicts(self) -> Dict[str, list]:
        """Scan existing subscriber files for ID conflicts."""
        conflicts = {}
        existing_ids = set()
        
        # Scan all kit directories
        for kit_dir in ["BOOK3", "BOOK", "BOSK"]:
            kit_path = self.subscribers_dir / kit_dir
            if not kit_path.exists():
                continue
                
            for json_file in kit_path.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    # Extract current identifier
                    current_id = data.get("subscriber_id", json_file.stem.replace("_BOOK3", "").replace("_BOOK", "").replace("_BOSK", ""))
                    
                    if current_id in existing_ids:
                        if current_id not in conflicts:
                            conflicts[current_id] = []
                        conflicts[current_id].append(str(json_file))
                    else:
                        existing_ids.add(current_id)
                        
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
        
        return conflicts
    
    def suggest_new_ids(self, conflict_files: list) -> Dict[str, str]:
        """Suggest new unique IDs for conflicting files."""
        suggestions = {}
        
        for file_path in conflict_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Extract subscriber info
                identity = data.get("identity", {})
                first_name = identity.get("first_name", "Unknown")
                last_name = identity.get("last_name", "Unknown")
                birth_date = identity.get("birth_date", data.get("dob", "Unknown"))
                current_id = data.get("subscriber_id", Path(file_path).stem)
                
                subscriber_info = SubscriberInfo(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    current_id=current_id
                )
                
                suggested_id = self.generate_unique_id(subscriber_info)
                suggestions[file_path] = suggested_id
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                suggestions[file_path] = f"ERROR_{e}"
        
        return suggestions
    
    def update_subscriber_file(self, file_path: str, new_id: str) -> bool:
        """Update a subscriber file with new ID."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Update subscriber_id
            data["subscriber_id"] = new_id
            
            # Update file path in registry
            if new_id in self.id_registry["used_ids"]:
                self.id_registry["used_ids"][new_id]["file_path"] = file_path
                self._save_registry()
            
            # Write updated file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error updating {file_path}: {e}")
            return False

def main():
    """Main function to analyze and fix subscriber ID conflicts."""
    project_root = Path(__file__).parent.parent.absolute()
    manager = SubscriberIDManager(project_root)
    
    print("🔍 SUBSCRIBER ID CONFLICT ANALYSIS")
    print("=" * 50)
    
    # Check for existing conflicts
    conflicts = manager.check_existing_conflicts()
    
    if not conflicts:
        print("✅ No subscriber ID conflicts found!")
        return
    
    print(f"⚠️  Found {len(conflicts)} conflicts:")
    print()
    
    for conflict_id, files in conflicts.items():
        print(f"🔴 Conflict ID: {conflict_id}")
        print(f"   Files affected: {len(files)}")
        
        for file_path in files:
            print(f"     - {file_path}")
        
        # Generate suggestions
        suggestions = manager.suggest_new_ids(files)
        print(f"   💡 Suggested new IDs:")
        
        for file_path, new_id in suggestions.items():
            file_name = Path(file_path).name
            print(f"     - {file_name} → {new_id}")
        
        print()
    
    # Ask user if they want to apply fixes
    print("🎯 RESOLUTION OPTIONS:")
    print("1. Apply suggested ID changes automatically")
    print("2. Show detailed analysis only")
    print("3. Exit without changes")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n🚀 Applying suggested changes...")
        
        total_updates = 0
        for conflict_id, files in conflicts.items():
            suggestions = manager.suggest_new_ids(files)
            
            for file_path, new_id in suggestions.items():
                if manager.update_subscriber_file(file_path, new_id):
                    print(f"  ✅ Updated {Path(file_path).name} → {new_id}")
                    total_updates += 1
                else:
                    print(f"  ❌ Failed to update {Path(file_path).name}")
        
        print(f"\n🎉 Updated {total_updates} subscriber files!")
        print(f"📁 Registry saved to: {manager.id_registry_file}")
    
    elif choice == "2":
        print("\n📋 Analysis complete. No changes made.")
    
    else:
        print("\n👋 Exiting without changes.")

if __name__ == "__main__":
    main()