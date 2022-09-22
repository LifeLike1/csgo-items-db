from dataclasses import dataclass

from . import _typings


@dataclass(repr=False, eq=False)
class FieldsCollector:
    """Collect origins, qualities, types, paints and rarities from game data."""

    items_game: _typings.ITEMS_GAME
    csgo_english: _typings.CSGO_ENGLISH
    items_schema: _typings.ITEMS_SCHEMA
    categories: _typings.CATEGORIES
    phases_mapping: _typings.PHASES_MAPPING

    # key to identify rarity
    _WEAPON_KEY: str = "weapon"
    _NON_WEAPON_KEY: str = "nonweapon"
    _CHARACTER_KEY: str = "character"

    _WEAR_MIN_DEFAULT: float = 0.06
    _WEAR_MAX_DEFAULT: float = 0.8

    def _parse_qualities(self) -> dict[str, str]:
        qualities = {}
        for quality_key, quality_data in self.items_game["qualities"].items():
            try:
                qualities[quality_data["value"]] = self.csgo_english[quality_key.lower()]
            except KeyError:
                pass
        return qualities

    def _find_item_name(self, defindex: str) -> str | None:
        item_data: dict[str, str] = self.items_game["items"][defindex]
        if "item_name" in item_data:
            weapon_hud: str = item_data["item_name"][1:]

        else:
            weapon_hud: str = self.items_game["prefabs"][item_data["prefab"]]["item_name"][1:]

        return self.csgo_english[weapon_hud.lower()]

    @staticmethod
    def _invert_dict(mapping: dict[str, str]) -> dict[str, str]:
        return {v: k for k, v in mapping.items()}

    def _find_category(self, defindex: str) -> str:
        categories_mapping = self._invert_dict(self.categories)

        for item_data in self.items_schema["items"]:
            if str(item_data["defindex"]) == defindex:
                return categories_mapping[self.csgo_english[item_data["item_type_name"][1:].lower()].lower()]

    def _find_description_type(self, defindex: str) -> str:
        prefab: str = self.items_game["items"][defindex]["prefab"]
        item_description_id: str = self.items_game["prefabs"][prefab]["item_description"][1:].lower()
        if item_description_id in self.csgo_english:
            return self.csgo_english[item_description_id]

    def _find_description_paint_kit(self, paintindex: str) -> str:
        description_string: str = self.items_game["paint_kits"][paintindex]["description_string"][1:].lower()
        description = self.csgo_english[description_string]
        if description := self.csgo_english[description_string]:
            return description.replace("\n\n", " ").replace("<i>", "").replace("</i>", "").replace('\"', "")

    def _parse_types(self) -> dict[str, dict[str, str]]:
        types = {}

        del self.items_game["items"]["default"]
        for defindex in self.items_game["items"].keys():
            try:
                types[defindex] = {
                    "name": self._find_item_name(defindex),
                    "category": self._find_category(defindex),
                }
                if description := self._find_description_type(defindex):
                    types[defindex]["description"] = description
            except KeyError:
                pass
        return types

    def _define_paints(self, paintindex: str) -> str:
        code_name: str = self.items_game["paint_kits"][paintindex]["description_tag"][1:]
        return self.csgo_english[code_name.lower()]

    def _find_paint_kit_colors(self, paintindex: str) -> list[str]:
        colors: list[str] = []
        i = 0 
        while True:
            try:
                color = self.items_game["paint_kits"][paintindex][f"color{i}"].replace(" ", ", ")
                colors.append(f"rgb({color})")
                i += 1
            except:
                break
        if len(colors) > 0:
            return colors

    def _parse_paints(self):
        # paints with paintindex bigger than 999/1000 are real?
        paints = {}
        for paintindex, paint_data in self.items_game["paint_kits"].items():
            try:
                paint = {
                    "name": self._define_paints(paintindex),
                    "wear_min": float(paint_data.get("wear_remap_min", self._WEAR_MIN_DEFAULT)),
                    "wear_max": float(paint_data.get("wear_remap_max", self._WEAR_MAX_DEFAULT)),
                    "colors": self._find_paint_kit_colors(paintindex),
                }

                if "doppler" in paint["name"].lower() and (phase := self.phases_mapping.get(paintindex)):
                    paint["phase"] = phase

                if description := self._find_description_paint_kit(paintindex):
                    paint["description"] = description

                paints[paintindex] = paint
            except KeyError:
                pass

        del paints["0"]  # exclude base(vanilla) weapon paint
        return paints

    def _parse_rarities(self) -> dict[str, dict[str, str]]:
        del self.items_game["rarities"]["unusual"]
        del self.items_game["rarities"]["default"]  # remove useless rarities
        rarities = {}
        for v in self.items_game["rarities"].values():
            rarity = {
                self._WEAPON_KEY: self.csgo_english[v["loc_key_weapon"].lower()],
                self._NON_WEAPON_KEY: self.csgo_english[v["loc_key"].lower()],
                "color": self.items_game["colors"][v["color"]]["hex_color"],
            }
            if character_rarity := self.csgo_english[v["loc_key_character"].lower()]:
                rarity[self._CHARACTER_KEY] = character_rarity

            rarities[v["value"]] = rarity

        return rarities

    def _parse_origins(self) -> dict[str, str]:
        return {str(origin_data["origin"]): origin_data["name"] for origin_data in self.items_schema["originNames"]}

    def __call__(self) -> tuple:
        """Parse all data to indexed format"""
        qualities = self._parse_qualities()
        types = self._parse_types()
        paints = self._parse_paints()

        rarities = self._parse_rarities()
        origins = self._parse_origins()

        return qualities, types, paints, rarities, origins
