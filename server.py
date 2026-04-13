"""
Cookidoo MCP Server

Main server file containing MCP tool definitions for interacting with Cookidoo.
"""

from fastmcp import FastMCP
from cookidoo_service import CookidooService, load_cookidoo_credentials
from schemas import CustomRecipe
import json
import datetime

# Initialize FastMCP server
mcp = FastMCP("cookidoo-mcp-server")

# Module-level state to store the authenticated session
_cookidoo_service: CookidooService | None = None
_cookidoo_api = None


@mcp.tool()
async def connect_to_cookidoo() -> str:
    """
    Authenticate with Cookidoo and store the session.

    This tool must be called before using other Cookidoo tools. It will:
    1. Load your Cookidoo credentials from the .env file
    2. Authenticate with the Cookidoo platform
    3. Store the authenticated session for use by other tools

    Returns:
        str: Success message confirming connection

    Raises:
        ValueError: If credentials are missing from .env file
        Exception: If authentication fails
    """
    global _cookidoo_service, _cookidoo_api

    try:
        # Load credentials from .env file
        email, password = load_cookidoo_credentials()

        # Create Cookidoo service instance
        _cookidoo_service = CookidooService(email, password)

        # Authenticate and get API client
        _cookidoo_api = await _cookidoo_service.login()

        return f"Successfully connected to Cookidoo as {email}"

    except ValueError as e:
        # Missing credentials
        return f"Configuration Error: {str(e)}\n\nPlease ensure your .env file contains COOKIDOO_EMAIL and COOKIDOO_PASSWORD"

    except Exception as e:
        # Authentication or other errors
        return f"Connection Failed: {str(e)}\n\nPlease check your credentials and try again."


@mcp.tool()
async def get_recipe_details(recipe_id: str) -> str:
    """
    Get detailed information about a specific recipe by its ID.

    Use this tool to get full details about a recipe for inspiration before creating
    your own custom recipe. You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The Cookidoo recipe ID (e.g., "r59322", "r907015")

    Returns:
        str: Detailed recipe information including ingredients, steps, cooking time, etc.

    Raises:
        Exception: If not connected or if the recipe is not found
    """
    global _cookidoo_api

    try:
        # Check if connected
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        # Get recipe details
        recipe = await _cookidoo_api.get_recipe_details(recipe_id)

        # Format the results
        result = f"Recipe Details:\n\n"
        result += f"Name: {recipe.name}\n"
        result += f"ID: {recipe.id}\n\n"

        if hasattr(recipe, 'serving_size'):
            result += f"Servings: {recipe.serving_size}\n"

        if hasattr(recipe, 'total_time'):
            result += f"Total Time: {recipe.total_time} minutes\n"

        if hasattr(recipe, 'difficulty'):
            result += f"Difficulty: {recipe.difficulty}\n"

        result += "\n"

        # Ingredients
        if hasattr(recipe, 'ingredients') and recipe.ingredients:
            result += "Ingredients:\n"
            for ingredient in recipe.ingredients:
                if hasattr(ingredient, 'name'):
                    result += f"  • {ingredient.name}"
                    if hasattr(ingredient, 'quantity') and ingredient.quantity:
                        result += f" - {ingredient.quantity}"
                    result += "\n"
            result += "\n"

        # Steps
        if hasattr(recipe, 'steps') and recipe.steps:
            result += "Steps:\n"
            for i, step in enumerate(recipe.steps, 1):
                if hasattr(step, 'description'):
                    result += f"{i}. {step.description}\n"
            result += "\n"

        # URL if available
        if hasattr(recipe, 'url') and recipe.url:
            result += f"URL: {recipe.url}\n"

        return result

    except Exception as e:
        return f"Failed to get recipe details: {str(e)}"


@mcp.tool()
async def generate_recipe_structure(
    name: str,
    ingredients: str,
    steps: str,
    servings: int = 4,
    prep_time: int = 30,
    total_time: int = 60,
    hints: str = "",
) -> str:
    """
    Generate and validate a recipe structure ready for upload to Cookidoo.

    This tool helps you structure your recipe data properly before uploading.
    It validates all fields and returns a JSON structure that can be used with
    the upload_custom_recipe tool.

    Args:
        name: Recipe name (required)
        ingredients: Ingredients list, one per line or comma-separated
        steps: Cooking steps, one per line or numbered
        servings: Number of servings (default: 4, range: 1-20)
        prep_time: Preparation time in minutes (default: 30)
        total_time: Total cooking time in minutes (default: 60)
        hints: Optional cooking tips, one per line or comma-separated

    Returns:
        str: Validated recipe structure in JSON format, ready for upload
    """
    try:
        # Parse ingredients (split by newlines or commas)
        ingredients_list = [
            ing.strip()
            for ing in (ingredients.split('\n') if '\n' in ingredients else ingredients.split(','))
            if ing.strip()
        ]

        # Parse steps (split by newlines or numbered steps)
        steps_list = [
            step.strip().lstrip('0123456789.)-• ')
            for step in steps.split('\n')
            if step.strip()
        ]

        # Parse hints if provided
        hints_list = None
        if hints:
            hints_list = [
                hint.strip()
                for hint in (hints.split('\n') if '\n' in hints else hints.split(','))
                if hint.strip()
            ]

        # Create and validate the recipe using Pydantic
        recipe = CustomRecipe(
            name=name,
            ingredients=ingredients_list,
            steps=steps_list,
            servings=servings,
            prep_time=prep_time,
            total_time=total_time,
            hints=hints_list
        )

        # Return formatted JSON
        recipe_json = recipe.model_dump_json(indent=2)

        return f"Recipe structure validated successfully!\n\n{recipe_json}\n\nYou can now use this with 'upload_custom_recipe'."

    except Exception as e:
        return f"Validation failed: {str(e)}\n\nPlease check your recipe data and try again."


@mcp.tool()
async def upload_custom_recipe(recipe_json: str) -> str:
    """
    Upload a custom recipe to your Cookidoo account.

    This tool creates a brand new recipe from scratch on your Cookidoo account.
    Use 'generate_recipe_structure' first to validate your recipe data, then
    pass the resulting JSON to this tool.

    Args:
        recipe_json: The validated recipe JSON from generate_recipe_structure

    Returns:
        str: Success message with the created recipe ID
    """
    global _cookidoo_service, _cookidoo_api

    try:
        # Check if connected
        if not _cookidoo_service or not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        # Parse and validate the recipe JSON
        try:
            recipe_data = json.loads(recipe_json)
            recipe = CustomRecipe(**recipe_data)
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {str(e)}"
        except Exception as e:
            return f"Invalid recipe data: {str(e)}"

        # Create the recipe using our custom service method
        recipe_id = await _cookidoo_service.create_custom_recipe(
            name=recipe.name,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            servings=recipe.servings,
            prep_time=recipe.prep_time,
            total_time=recipe.total_time,
            hints=recipe.hints
        )

        # Get localization for URL
        localization = _cookidoo_api.localization
        recipe_url = f"https://{localization.url}/recipes/custom-recipes/{recipe_id}"

        return f"Recipe '{recipe.name}' created successfully!\n\nRecipe ID: {recipe_id}\nURL: {recipe_url}\n\nYour recipe is now saved in your Cookidoo account!"

    except Exception as e:
        return f"Upload failed: {str(e)}"


# ================== HELPERS ==================

def _parse_list_param(param) -> list[str]:
    """Parse a parameter that may be a list or comma-separated string."""
    if isinstance(param, list):
        return [str(item).strip() for item in param if str(item).strip()]
    elif isinstance(param, str):
        return [item.strip() for item in param.split(',') if item.strip()]
    return []


def _parse_date(date_str: str) -> datetime.date:
    """Parse a YYYY-MM-DD string into a datetime.date."""
    return datetime.date.fromisoformat(date_str)


# ================== CALENDAR ==================

@mcp.tool()
async def get_calendar_week(year: int, week_number: int) -> str:
    """
    Fetch all recipes scheduled in the Cookidoo meal planner for a given ISO week.

    You must be connected first using connect_to_cookidoo.

    Args:
        year: The calendar year (e.g., 2025)
        week_number: The ISO week number (1–53)

    Returns:
        str: Recipes scheduled for each day of the week
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        # API takes any date in the desired week; use Monday (day=1)
        monday = datetime.date.fromisocalendar(year, week_number, 1)
        days = await _cookidoo_api.get_recipes_in_calendar_week(day=monday)

        if not days:
            return f"No recipes scheduled for week {week_number} of {year}."

        result = f"Meal plan for week {week_number} of {year}:\n\n"
        for day in days:
            title = day.title if hasattr(day, 'title') else str(day)
            standard_recipes = day.recipes if hasattr(day, 'recipes') else []
            custom_ids = day.customer_recipe_ids if hasattr(day, 'customer_recipe_ids') else []

            result += f"{title}:\n"
            if not standard_recipes and not custom_ids:
                result += "  (nothing planned)\n"
            for recipe in standard_recipes:
                result += f"  • {recipe.name} (ID: {recipe.id})"
                if hasattr(recipe, 'total_time') and recipe.total_time:
                    result += f" — {recipe.total_time} min"
                result += "\n"
            for cid in custom_ids:
                result += f"  • Custom recipe (ID: {cid})\n"
            result += "\n"

        return result.rstrip()

    except Exception as e:
        return f"Failed to get calendar week: {str(e)}"


@mcp.tool()
async def add_recipe_to_calendar(recipe_id: str, date: str) -> str:
    """
    Schedule a standard Cookidoo recipe to a specific date in the meal planner.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The Cookidoo recipe ID (e.g., "r59322")
        date: The date to schedule the recipe (YYYY-MM-DD format)

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        day = _parse_date(date)
        await _cookidoo_api.add_recipes_to_calendar(day=day, recipe_ids=[recipe_id])
        return f"Recipe '{recipe_id}' added to calendar on {date}."

    except Exception as e:
        return f"Failed to add recipe to calendar: {str(e)}"


@mcp.tool()
async def add_custom_recipe_to_calendar(recipe_id: str, date: str) -> str:
    """
    Schedule a custom/uploaded recipe to a specific date in the meal planner.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The custom recipe ID
        date: The date to schedule the recipe (YYYY-MM-DD format)

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        day = _parse_date(date)
        await _cookidoo_api.add_custom_recipes_to_calendar(day=day, recipe_ids=[recipe_id])
        return f"Custom recipe '{recipe_id}' added to calendar on {date}."

    except Exception as e:
        return f"Failed to add custom recipe to calendar: {str(e)}"


@mcp.tool()
async def remove_recipe_from_calendar(recipe_id: str, date: str) -> str:
    """
    Remove a standard recipe from a specific date in the meal planner.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The Cookidoo recipe ID to remove
        date: The date to remove the recipe from (YYYY-MM-DD format)

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        day = _parse_date(date)
        await _cookidoo_api.remove_recipe_from_calendar(day=day, recipe_id=recipe_id)
        return f"Recipe '{recipe_id}' removed from calendar on {date}."

    except Exception as e:
        return f"Failed to remove recipe from calendar: {str(e)}"


@mcp.tool()
async def remove_custom_recipe_from_calendar(recipe_id: str, date: str) -> str:
    """
    Remove a custom recipe from a specific date in the meal planner.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The custom recipe ID to remove
        date: The date to remove the recipe from (YYYY-MM-DD format)

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        day = _parse_date(date)
        await _cookidoo_api.remove_custom_recipe_from_calendar(day=day, recipe_id=recipe_id)
        return f"Custom recipe '{recipe_id}' removed from calendar on {date}."

    except Exception as e:
        return f"Failed to remove custom recipe from calendar: {str(e)}"


# ================== SHOPPING LIST ==================

@mcp.tool()
async def get_shopping_list() -> str:
    """
    Return the current shopping list recipes.

    You must be connected first using connect_to_cookidoo.

    Returns:
        str: List of recipes currently on the shopping list
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        recipes = await _cookidoo_api.get_shopping_list_recipes()

        if not recipes:
            return "Your shopping list is empty."

        result = f"Shopping list recipes ({len(recipes)} total):\n\n"
        for i, recipe in enumerate(recipes, 1):
            result += f"{i}. {recipe.name} (ID: {recipe.id})\n"

        return result

    except Exception as e:
        return f"Failed to get shopping list: {str(e)}"


@mcp.tool()
async def get_ingredient_items() -> str:
    """
    Return the full itemised ingredient list from the shopping list.

    You must be connected first using connect_to_cookidoo.

    Returns:
        str: All ingredient items with ownership status
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        items = await _cookidoo_api.get_ingredient_items()

        if not items:
            return "No ingredient items on your shopping list."

        owned = [i for i in items if i.is_owned]
        needed = [i for i in items if not i.is_owned]

        result = f"Ingredient items ({len(items)} total):\n\n"

        if needed:
            result += f"To buy ({len(needed)}):\n"
            for item in needed:
                result += f"  • {item.name}"
                if item.description:
                    result += f" — {item.description}"
                result += f" (ID: {item.id})\n"

        if owned:
            result += f"\nAlready owned ({len(owned)}):\n"
            for item in owned:
                result += f"  ✓ {item.name} (ID: {item.id})\n"

        return result

    except Exception as e:
        return f"Failed to get ingredient items: {str(e)}"


@mcp.tool()
async def add_recipes_to_shopping_list(recipe_ids: str) -> str:
    """
    Add one or more standard recipes' ingredients to the shopping list.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_ids: One or more recipe IDs, as a list or comma-separated string
                    (e.g., "r59322,r907015" or ["r59322", "r907015"])

    Returns:
        str: Confirmation with the updated ingredient count
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        ids = _parse_list_param(recipe_ids)
        if not ids:
            return "No recipe IDs provided."

        items = await _cookidoo_api.add_ingredient_items_for_recipes(recipe_ids=ids)
        return f"Added ingredients for {len(ids)} recipe(s) to shopping list. Total ingredient items: {len(items)}."

    except Exception as e:
        return f"Failed to add recipes to shopping list: {str(e)}"


@mcp.tool()
async def add_custom_recipes_to_shopping_list(recipe_ids: str) -> str:
    """
    Add one or more custom recipes' ingredients to the shopping list.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_ids: One or more custom recipe IDs, as a list or comma-separated string

    Returns:
        str: Confirmation with the updated ingredient count
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        ids = _parse_list_param(recipe_ids)
        if not ids:
            return "No recipe IDs provided."

        items = await _cookidoo_api.add_ingredient_items_for_custom_recipes(recipe_ids=ids)
        return f"Added ingredients for {len(ids)} custom recipe(s) to shopping list. Total ingredient items: {len(items)}."

    except Exception as e:
        return f"Failed to add custom recipes to shopping list: {str(e)}"


@mcp.tool()
async def add_additional_items(items: str) -> str:
    """
    Add freeform items to the shopping list that are not tied to any recipe.

    You must be connected first using connect_to_cookidoo.

    Args:
        items: Items to add, as a list or comma-separated string
               (e.g., "olive oil, oat milk" or ["olive oil", "oat milk"])

    Returns:
        str: Confirmation with the added items
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        item_names = _parse_list_param(items)
        if not item_names:
            return "No items provided."

        added = await _cookidoo_api.add_additional_items(additional_item_names=item_names)

        result = f"Added {len(added)} item(s) to shopping list:\n"
        for item in added:
            result += f"  • {item.name}\n"

        return result

    except Exception as e:
        return f"Failed to add additional items: {str(e)}"


@mcp.tool()
async def edit_ingredient_items_ownership(item_ids: str, owned: bool) -> str:
    """
    Mark ingredient items as already owned (in the fridge) to exclude them from shopping.

    You must be connected first using connect_to_cookidoo.

    Args:
        item_ids: One or more ingredient item IDs, as a list or comma-separated string
        owned: True to mark as already owned, False to mark as needed

    Returns:
        str: Confirmation of updated items
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        ids = set(_parse_list_param(item_ids))
        if not ids:
            return "No item IDs provided."

        # Fetch current items and filter to those we want to update
        all_items = await _cookidoo_api.get_ingredient_items()
        matching = [item for item in all_items if item.id in ids]

        if not matching:
            return f"No ingredient items found with the provided IDs: {', '.join(ids)}"

        # Update ownership flag on each matched item
        for item in matching:
            item.is_owned = owned

        updated = await _cookidoo_api.edit_ingredient_items_ownership(ingredient_items=matching)

        status = "owned" if owned else "needed"
        result = f"Marked {len(updated)} item(s) as {status}:\n"
        for item in updated:
            result += f"  • {item.name}\n"

        return result

    except Exception as e:
        return f"Failed to update ingredient ownership: {str(e)}"


@mcp.tool()
async def clear_shopping_list() -> str:
    """
    Wipe the shopping list clean, removing all recipes and ingredient items.

    You must be connected first using connect_to_cookidoo.

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        await _cookidoo_api.clear_shopping_list()
        return "Shopping list cleared successfully."

    except Exception as e:
        return f"Failed to clear shopping list: {str(e)}"


# ================== COLLECTIONS ==================

@mcp.tool()
async def get_custom_collections() -> str:
    """
    List all custom recipe collections in your Cookidoo account.

    You must be connected first using connect_to_cookidoo.

    Returns:
        str: List of custom collections with their IDs and recipe counts
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        collections = await _cookidoo_api.get_custom_collections()

        if not collections:
            return "No custom collections found."

        result = f"Custom collections ({len(collections)} total):\n\n"
        for i, col in enumerate(collections, 1):
            result += f"{i}. {col.name} (ID: {col.id})"
            if col.description:
                result += f" — {col.description}"
            # Count recipes across all chapters
            total_recipes = sum(
                len(ch.recipes) for ch in col.chapters if hasattr(ch, 'recipes')
            ) if hasattr(col, 'chapters') else 0
            if total_recipes:
                result += f" [{total_recipes} recipe(s)]"
            result += "\n"

        return result

    except Exception as e:
        return f"Failed to get custom collections: {str(e)}"


@mcp.tool()
async def add_custom_collection(name: str) -> str:
    """
    Create a new custom recipe collection.

    You must be connected first using connect_to_cookidoo.

    Args:
        name: The name for the new collection

    Returns:
        str: Confirmation with the new collection's ID
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        collection = await _cookidoo_api.add_custom_collection(custom_collection_name=name)

        result = f"Collection '{name}' created successfully!"
        if hasattr(collection, 'id') and collection.id:
            result += f"\nCollection ID: {collection.id}"

        return result

    except Exception as e:
        return f"Failed to create collection: {str(e)}"


@mcp.tool()
async def remove_custom_collection(collection_id: str) -> str:
    """
    Delete a custom recipe collection.

    You must be connected first using connect_to_cookidoo.

    Args:
        collection_id: The ID of the collection to delete

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        await _cookidoo_api.remove_custom_collection(custom_collection_id=collection_id)
        return f"Collection '{collection_id}' deleted successfully."

    except Exception as e:
        return f"Failed to delete collection: {str(e)}"


@mcp.tool()
async def add_recipes_to_custom_collection(collection_id: str, recipe_ids: str) -> str:
    """
    Add one or more recipes to a custom collection.

    You must be connected first using connect_to_cookidoo.

    Args:
        collection_id: The ID of the target collection
        recipe_ids: One or more recipe IDs, as a list or comma-separated string

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        ids = _parse_list_param(recipe_ids)
        if not ids:
            return "No recipe IDs provided."

        await _cookidoo_api.add_recipes_to_custom_collection(
            custom_collection_id=collection_id, recipe_ids=ids
        )
        return f"Added {len(ids)} recipe(s) to collection '{collection_id}'."

    except Exception as e:
        return f"Failed to add recipes to collection: {str(e)}"


@mcp.tool()
async def remove_recipe_from_custom_collection(collection_id: str, recipe_id: str) -> str:
    """
    Remove a recipe from a custom collection.

    You must be connected first using connect_to_cookidoo.

    Args:
        collection_id: The ID of the collection
        recipe_id: The ID of the recipe to remove

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        await _cookidoo_api.remove_recipe_from_custom_collection(
            custom_collection_id=collection_id, recipe_id=recipe_id
        )
        return f"Recipe '{recipe_id}' removed from collection '{collection_id}'."

    except Exception as e:
        return f"Failed to remove recipe from collection: {str(e)}"


# ================== CUSTOM RECIPE MANAGEMENT ==================

@mcp.tool()
async def get_custom_recipe(recipe_id: str) -> str:
    """
    Fetch full details of a previously uploaded custom recipe.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The custom recipe ID

    Returns:
        str: Full recipe details including ingredients and instructions
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        recipe = await _cookidoo_api.get_custom_recipe(id=recipe_id)

        result = "Custom Recipe Details:\n\n"
        result += f"Name: {recipe.name}\n"
        result += f"ID: {recipe.id}\n"
        if recipe.serving_size:
            result += f"Servings: {recipe.serving_size}\n"
        if recipe.total_time:
            result += f"Total Time: {recipe.total_time} min\n"
        if recipe.active_time:
            result += f"Active Time: {recipe.active_time} min\n"
        if recipe.url:
            result += f"URL: {recipe.url}\n"

        result += "\n"

        if recipe.ingredients:
            result += "Ingredients:\n"
            for ing in recipe.ingredients:
                result += f"  • {ing}\n"
            result += "\n"

        if recipe.instructions:
            result += "Instructions:\n"
            for i, step in enumerate(recipe.instructions, 1):
                result += f"{i}. {step}\n"

        return result

    except Exception as e:
        return f"Failed to get custom recipe: {str(e)}"


@mcp.tool()
async def remove_custom_recipe(recipe_id: str) -> str:
    """
    Delete a custom recipe from your Cookidoo account.

    You must be connected first using connect_to_cookidoo.

    Args:
        recipe_id: The custom recipe ID to delete

    Returns:
        str: Confirmation message
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        await _cookidoo_api.remove_custom_recipe(custom_recipe_id=recipe_id)
        return f"Custom recipe '{recipe_id}' deleted successfully."

    except Exception as e:
        return f"Failed to delete custom recipe: {str(e)}"


@mcp.tool()
async def list_custom_recipes() -> str:
    """
    List all custom recipes in your Cookidoo account.

    Note: The Cookidoo API does not provide a direct endpoint for listing all custom
    recipes. This tool retrieves them via your custom collections by iterating through
    each collection's chapters. Recipes not added to any collection will not appear
    here — browse your collections directly on Cookidoo to see all custom recipes.

    You must be connected first using connect_to_cookidoo.

    Returns:
        str: Custom recipes found across all custom collections
    """
    global _cookidoo_api

    try:
        if not _cookidoo_api:
            return "Not connected. Please run 'connect_to_cookidoo' first."

        collections = await _cookidoo_api.get_custom_collections()

        if not collections:
            return (
                "No custom collections found. Custom recipes can only be listed via collections.\n"
                "Add your custom recipes to a collection in Cookidoo, then try again."
            )

        seen_ids: set[str] = set()
        all_recipes: list[str] = []

        for col in collections:
            col_name = col.name
            chapters = col.chapters if hasattr(col, 'chapters') else []

            for chapter in chapters:
                chapter_recipes = chapter.recipes if hasattr(chapter, 'recipes') else []
                for recipe in chapter_recipes:
                    if recipe.id in seen_ids:
                        continue
                    seen_ids.add(recipe.id)
                    entry = f"  • {recipe.name} (ID: {recipe.id})"
                    if hasattr(recipe, 'total_time') and recipe.total_time:
                        entry += f" — {recipe.total_time} min"
                    entry += f" [collection: {col_name}]"
                    all_recipes.append(entry)

        if not all_recipes:
            return (
                "Your custom collections exist but contain no recipes.\n\n"
                "Note: The Cookidoo API has no direct listing endpoint for custom recipes. "
                "To view them here, add your custom recipes to a collection on Cookidoo first."
            )

        result = (
            f"Custom recipes found across {len(collections)} collection(s) "
            f"({len(all_recipes)} unique total):\n\n"
        )
        result += "\n".join(all_recipes)
        return result

    except Exception as e:
        return f"Failed to list custom recipes: {str(e)}"
