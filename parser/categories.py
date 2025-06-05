import json
import os
from pathlib import Path

class CategoryStructure:
    def __init__(self, json_path: str = None):
        """
        Initialize category structure
        
        Args:
            json_path (str, optional): Path to JSON file with categories.
                By default looks for categories.json in the data folder
        """
        if json_path is None:
            # Define path to JSON file relative to current file
            current_dir = Path(__file__).parent
            json_path = current_dir / 'data' / 'categories.json'

        # Initialize empty structure
        self.categories = {}
        
        # Load categories from JSON if file exists
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error reading JSON file: {e}")
            except Exception as e:
                print(f"Error loading categories: {e}")

    def save_to_json(self, json_path: str = None) -> bool:
        """
        Save current category structure to JSON file
        
        Args:
            json_path (str, optional): Path to JSON file.
                By default uses path from constructor
                
        Returns:
            bool: True if save successful, False otherwise
        """
        if json_path is None:
            json_path = Path(__file__).parent / 'data' / 'categories.json'

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving categories: {e}")
            return False

    def add_category(self, parent_code: str = None, code: str = None, name: str = None) -> bool:
        """
        Add new category to hierarchy
        
        Args:
            parent_code (str, optional): Parent category code. None for first level category
            code (str): New category code
            name (str): New category name
            
        Returns:
            bool: True if category successfully added, False if not
        """
        if not code or not name:
            return False

        if not parent_code:
            # Adding first level category
            if code not in self.categories:
                self.categories[code] = {
                    "name": name,
                    "subcategories": {}
                }
                return True
            return False

        # Finding parent category
        def find_and_add(categories, target_code):
            if target_code in categories:
                categories[target_code]["subcategories"][code] = {
                    "name": name,
                    "subcategories": {}
                }
                return True
            for cat in categories.values():
                if find_and_add(cat["subcategories"], target_code):
                    return True
            return False

        return find_and_add(self.categories, parent_code)

    def get_category(self, *codes) -> dict:
        """
        Get category by path of codes
        
        Args:
            *codes: Sequence of category codes (path in hierarchy)
            
        Returns:
            dict: Category or None if not found
        """
        current = self.categories
        for code in codes:
            if code not in current:
                return None
            current = current[code]
            if "subcategories" in current:
                current = current["subcategories"]
        return current

    def get_category_name(self, *codes) -> str:
        """
        Get category name by path of codes
        
        Args:
            *codes: Sequence of category codes
            
        Returns:
            str: Category name or None if category not found
        """
        category = self.get_category(*codes[:-1])
        if category and codes[-1] in category:
            return category[codes[-1]]["name"]
        return None

    def get_subcategories(self, *parent_codes) -> dict:
        """
        Get all subcategories for given category
        
        Args:
            *parent_codes: Sequence of parent category codes
            
        Returns:
            dict: Dictionary of subcategories
        """
        category = self.get_category(*parent_codes)
        return category if category else {}
