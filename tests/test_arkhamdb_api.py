from unittest.mock import Mock

import requests

from arkhamdb_api import ArkhamDBAPI


def reset_api_cache():
    ArkhamDBAPI._shared_cards_cache = {}
    ArkhamDBAPI._shared_all_cards_cache = None
    ArkhamDBAPI._shared_search_index = []
    ArkhamDBAPI._shared_index_by_code = {}
    ArkhamDBAPI._shared_loading = False


def test_search_orders_matches_and_filters_encounters():
    reset_api_cache()
    api = ArkhamDBAPI()
    api._set_shared_data(
        [
            {"code": "1", "name": "Agnes", "faction_code": "mystic", "type_code": "investigator"},
            {"code": "2", "name": "Agnes Enemy", "faction_code": "mythos", "type_code": "enemy"},
            {"code": "3", "name": "Young Agnes", "faction_code": "mystic", "type_code": "asset"},
        ]
    )
    assert [card["code"] for card in api.search_cards("Agnes", include_encounter=False)] == [
        "1",
        "3",
    ]


def test_get_card_uses_timeout_and_handles_network_error():
    reset_api_cache()
    api = ArkhamDBAPI()
    api._session.get = Mock(side_effect=requests.Timeout("offline"))
    assert api.get_card("01004") is None
    assert api._session.get.call_count == 2
    assert all(call.kwargs["timeout"] == 10 for call in api._session.get.call_args_list)
