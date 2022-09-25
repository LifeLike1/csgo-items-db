from gc import collect
import re
from dataclasses import dataclass

from . import _typings
from ._vpk_extractor import VpkExtractor


@dataclass(repr=False, eq=False)
class CollectionsCollector:
    """Collect collections"""

    pak: VpkExtractor
    items_game: _typings.ITEMS_GAME
    csgo_english: _typings.CSGO_ENGLISH
    items_schema: _typings.ITEMS_SCHEMA


    def _find_image(self, defindex: str) -> str:
        for item in self.items_schema["items"]:
            if item["defindex"] == int(defindex):
                return item["image_url"] or item["image_url_large"]

    def _find_item_indexes(self, item_names: str) -> str:
        paint_name, type_name = re.findall(r"\[(.+)](.+)", item_names)[0]
        for defindex, type_data in self.items_game["items"].items():
            if type_data["name"] == type_name:
                for paint_index, paint_data in self.items_game["paint_kits"].items():
                    if paint_data["name"] == paint_name:
                        return "[" + paint_index + "]" + defindex

    def _find_items(self, set_name: str) -> list[str]:
        item_set: dict[str, dict[str, str] | str] = self.items_game["item_sets"][set_name]
        return [self._find_item_indexes(item_names) for item_names in item_set["items"].keys()]

    def __call__(self) -> dict[str, dict[str, str | list[str]]]:
        collections = {}
        # replace with loop through item_sets, inner loop to check if collection has souvenirs
        for defindex, item_data in self.items_game["items"].items():
            try:
                if item_data["prefab"] == "weapon_case_base" and "ItemSet" in item_data["tags"]:

                    # Check if the collection is already added, valve has some duplicates
                    collection_name = self.csgo_english[item_data["item_name"][1:].lower()]
                    skip_collection = False
                    for key in collections.keys():
                        if collections[key] == collection_name and skip_collection == False:
                            skip_collection = True
                            
                    if skip_collection == True:
                        continue
                    

                    has_souvenirs = False
                    for defindex_inner, item_data_inner in self.items_game["items"].items():
                        try:
                            if has_souvenirs == True:
                                continue
                            if item_data_inner["prefab"] != "weapon_case_souvenirpkg":
                                continue
                            if "ItemSet" not in item_data_inner["tags"]:
                                continue
                            if item_data_inner["tags"]["ItemSet"]["tag_value"] != item_data["tags"]["ItemSet"]["tag_value"]:
                                continue
                            if item_data_inner["item_name"] == item_data["item_name"]:
                                continue

                            has_souvenirs = True
                        except KeyError:
                            continue

                    collections.update(
                        {
                            collection_name: {
                                "extra_id": defindex,
                                "image": self.pak.get_image_url("set_icons", item_data["tags"]["ItemSet"]["tag_value"]),
                                "items": self._find_items(item_data["tags"]["ItemSet"]["tag_value"]),
                                "souvenirs": has_souvenirs,
                            }
                        }
                    )
            except KeyError:
                continue
        
        for collection_id, collection_data in self.items_game["item_sets"].items():
            try:
                collection_name = self.csgo_english[collection_data["name"][1:].lower()]
                
                if collection_name in collections.keys():
                    continue

                if "_characters" in collection_id:
                    continue
                
                collections.update(
                    {
                        collection_name: {
                            "image": self.pak.get_image_url("set_icons", collection_id),
                            "items": self._find_items(collection_id),
                            "souvenirs": False,
                        }
                    }
                )

            except KeyError:
                continue

        return collections
