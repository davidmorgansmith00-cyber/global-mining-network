from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = ROOT / "content" / "schema"
REQUIRED_CONTENT_TYPES = ("hardware", "buildings", "research", "recipes", "events")


class ContentValidator:
    def __init__(self, schema_root: Path | None = None) -> None:
        self._schema_root = schema_root or SCHEMA_ROOT
        self._schema_cache: dict[str, dict[str, Any]] = {}

    def load_schema(self, schema_name: str) -> dict[str, Any]:
        if schema_name not in self._schema_cache:
            path = self._schema_root / f"{schema_name}.schema.json"
            self._schema_cache[schema_name] = json.loads(path.read_text(encoding="utf-8"))
        return self._schema_cache[schema_name]

    def validate_schema(self, content: Any, schema: dict[str, Any]) -> list[str]:
        validator = Draft7Validator(schema)
        errors: list[str] = []
        for error in sorted(validator.iter_errors(content), key=lambda item: tuple(str(part) for part in item.absolute_path)):
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            errors.append(f"{location}: {error.message}")
        return errors

    def validate_content_pack(self, content: dict[str, Any], impact_notes: str | None = None) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        for content_type in REQUIRED_CONTENT_TYPES:
            if content_type not in content:
                errors.append(f"missing content type: {content_type}")
                continue
            schema_errors = self.validate_schema(content[content_type], self.load_schema(content_type))
            errors.extend(f"{content_type}: {message}" for message in schema_errors)

        errors.extend(self.check_orphan_unlocks(content))
        errors.extend(self.check_circular_dependencies(content))
        errors.extend(self.check_balance_sanity(content))
        warnings.extend(self.check_economy_impact(content, impact_notes))
        return errors, warnings

    def check_orphan_unlocks(self, content: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        research_ids = {str(item.get("id", "")).strip() for item in content.get("research", []) if item.get("id")}

        for item in content.get("research", []):
            unlock_condition = item.get("unlock_condition", {})
            dependency_id = None
            if isinstance(unlock_condition, dict):
                dependency_id = unlock_condition.get("research_id")
            if dependency_id and dependency_id not in research_ids:
                errors.append(f"orphan unlock: research:{item.get('id')} references missing research {dependency_id}")

        for collection_name in ("hardware", "buildings", "recipes"):
            for item in content.get(collection_name, []):
                dependency_id = item.get("unlock_research_id")
                if dependency_id and dependency_id not in research_ids:
                    item_id = item.get("id") or item.get("output_item_id") or "unknown"
                    errors.append(
                        f"orphan unlock: {collection_name}:{item_id} references missing research {dependency_id}"
                    )
        return sorted(set(errors))

    def check_circular_dependencies(self, content: dict[str, Any]) -> list[str]:
        graph: dict[str, list[str]] = {}
        for item in content.get("research", []):
            research_id = str(item.get("id", "")).strip()
            if not research_id:
                continue
            unlock_condition = item.get("unlock_condition", {})
            dependencies: list[str] = []
            if isinstance(unlock_condition, dict):
                dependency_id = unlock_condition.get("research_id")
                if dependency_id:
                    dependencies.append(str(dependency_id).strip())
            for dependency_id in item.get("prerequisite_ids", []):
                normalized = str(dependency_id).strip()
                if normalized:
                    dependencies.append(normalized)
            graph[research_id] = dependencies

        cycles: set[str] = set()
        visited: set[str] = set()
        active_stack: list[str] = []

        def visit(node: str) -> None:
            if node in active_stack:
                start_index = active_stack.index(node)
                cycle = active_stack[start_index:] + [node]
                cycles.add(f"circular dependency: {' -> '.join(cycle)}")
                return
            if node in visited:
                return

            visited.add(node)
            active_stack.append(node)
            for dependency in graph.get(node, []):
                if dependency in graph:
                    visit(dependency)
            active_stack.pop()

        for node in graph:
            visit(node)

        return sorted(cycles)

    def check_balance_sanity(self, content: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        known_item_ids = self._collect_known_item_ids(content)

        for recipe in content.get("recipes", []):
            recipe_id = str(recipe.get("id") or f"{recipe.get('input_item_id')}->{recipe.get('output_item_id')}").strip()
            input_item_id = str(recipe.get("input_item_id", "")).strip()
            output_item_id = str(recipe.get("output_item_id", "")).strip()
            try:
                input_quantity = int(recipe.get("input_quantity", 1))
            except (TypeError, ValueError):
                input_quantity = 0
            try:
                output_quantity = int(recipe.get("output_quantity", 1))
            except (TypeError, ValueError):
                output_quantity = 0
            try:
                duration_seconds = int(recipe.get("duration_seconds", 0))
            except (TypeError, ValueError):
                duration_seconds = 0
            try:
                cost_credits = int(recipe.get("cost_credits", 0))
            except (TypeError, ValueError):
                cost_credits = -1

            if duration_seconds <= 0:
                errors.append(f"impossible recipe: {recipe_id} has non-positive duration")
            if cost_credits < 0:
                errors.append(f"impossible recipe: {recipe_id} has negative cost")
            if input_quantity <= 0:
                errors.append(f"impossible recipe: {recipe_id} has non-positive input quantity")
            if output_quantity <= 0:
                errors.append(f"impossible recipe: {recipe_id} has non-positive output quantity")
            if input_item_id == output_item_id:
                errors.append(f"impossible recipe: {recipe_id} produces the same item it consumes")
            if input_item_id not in known_item_ids:
                errors.append(f"impossible recipe: {recipe_id} references unknown input item {input_item_id}")
            if output_item_id not in known_item_ids:
                errors.append(f"impossible recipe: {recipe_id} references unknown output item {output_item_id}")

        return sorted(set(errors))

    def check_economy_impact(self, content: dict[str, Any], impact_notes: str | None) -> list[str]:
        del content
        if impact_notes and impact_notes.strip():
            return []
        return ["missing economy impact notes"]

    @staticmethod
    def _collect_known_item_ids(content: dict[str, Any]) -> set[str]:
        known_ids: set[str] = set()
        for collection_name in ("hardware", "buildings"):
            for item in content.get(collection_name, []):
                item_id = str(item.get("id", "")).strip()
                if item_id:
                    known_ids.add(item_id)
        for recipe in content.get("recipes", []):
            output_item_id = str(recipe.get("output_item_id", "")).strip()
            if output_item_id:
                known_ids.add(output_item_id)
        return known_ids
