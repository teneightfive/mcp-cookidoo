# Cookidoo MCP Server

An MCP (Model Context Protocol) server for interacting with the Thermomix Cookidoo platform, built with `fastmcp`.

> **Disclaimer:** This is an unofficial project. The developers are not affiliated with, endorsed by, or connected to Cookidoo, Vorwerk, Thermomix, or any of their subsidiaries or trademarks.

## Features

- **Authentication**: Connect to your Cookidoo account securely
- **Recipe Details**: Fetch detailed recipe information by ID
- **Custom Recipes**: Structure, upload, retrieve, and delete custom recipes
- **Meal Planner**: View and manage your weekly calendar
- **Shopping List**: Add recipes, manage ingredients, and clear the list
- **Collections**: Create and organise custom recipe collections

## Setup

1. **Clone the repository and navigate to the project directory**

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your credentials:**
   ```bash
   cp .env.example .env
   # Edit .env with your Cookidoo email and password
   ```

5. **Run the MCP server:**
   ```bash
   fastmcp run server.py
   ```

## Available Tools

Call `connect_to_cookidoo` first — it must be run before any other tool.

### Authentication

| Tool | Description |
|---|---|
| `connect_to_cookidoo` | Authenticate with Cookidoo using credentials from `.env` |

### Recipes

| Tool | Parameters | Description |
|---|---|---|
| `get_recipe_details` | `recipe_id` | Fetch full details of a standard Cookidoo recipe |
| `generate_recipe_structure` | `name`, `ingredients`, `steps`, `servings`, `prep_time`, `total_time`, `hints` | Validate and structure a new recipe ready for upload |
| `upload_custom_recipe` | `recipe_json` | Upload a structured recipe to your Cookidoo account |

### Meal Planner (Calendar)

| Tool | Parameters | Description |
|---|---|---|
| `get_calendar_week` | `year`, `week_number` | Fetch all recipes planned for an ISO week |
| `add_recipe_to_calendar` | `recipe_id`, `date` | Schedule a standard recipe on a date (YYYY-MM-DD) |
| `add_custom_recipe_to_calendar` | `recipe_id`, `date` | Schedule a custom recipe on a date (YYYY-MM-DD) |
| `remove_recipe_from_calendar` | `recipe_id`, `date` | Remove a standard recipe from a date |
| `remove_custom_recipe_from_calendar` | `recipe_id`, `date` | Remove a custom recipe from a date |

### Shopping List

| Tool | Parameters | Description |
|---|---|---|
| `get_shopping_list` | — | List all recipes currently on the shopping list |
| `get_ingredient_items` | — | List all ingredient items, grouped by owned/needed |
| `add_recipes_to_shopping_list` | `recipe_ids` | Add standard recipe ingredients to the shopping list |
| `add_custom_recipes_to_shopping_list` | `recipe_ids` | Add custom recipe ingredients to the shopping list |
| `add_additional_items` | `items` | Add freeform items not tied to a recipe (e.g. "olive oil") |
| `edit_ingredient_items_ownership` | `item_ids`, `owned` | Mark ingredients as already owned to skip them at the shop |
| `clear_shopping_list` | — | Wipe the shopping list clean |

`recipe_ids` and `item_ids` accept either a Python list or a comma-separated string, e.g. `"r59322,r907015"`.

### Collections

| Tool | Parameters | Description |
|---|---|---|
| `get_custom_collections` | — | List all custom collections |
| `add_custom_collection` | `name` | Create a new collection |
| `remove_custom_collection` | `collection_id` | Delete a collection |
| `add_recipes_to_custom_collection` | `collection_id`, `recipe_ids` | Add recipes to a collection |
| `remove_recipe_from_custom_collection` | `collection_id`, `recipe_id` | Remove a recipe from a collection |

### Custom Recipe Management

| Tool | Parameters | Description |
|---|---|---|
| `get_custom_recipe` | `recipe_id` | Fetch full details of a custom recipe |
| `remove_custom_recipe` | `recipe_id` | Delete a custom recipe |
| `list_custom_recipes` | — | List custom recipes via collections (see note below) |

> **Note on `list_custom_recipes`:** The Cookidoo API does not expose a direct endpoint for listing all custom recipes. This tool retrieves them by iterating through your custom collections. Recipes not added to any collection will not appear — browse your collections on Cookidoo directly to see all custom recipes.

## Acknowledgments

This project is built on top of the [cookidoo-api](https://github.com/miaucl/cookidoo-api), which provides the Python interface to interact with the Cookidoo platform. Special thanks for making this integration possible!

## License

MIT
