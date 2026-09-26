"""Conservative semantic mapping for the original builder's navigation."""


def infer_navigation_mapping(design, responsive):
    elements = design.get("visibilityElements", [])
    changes = {item["path"]: item for item in responsive.get("visibility_changes", [])}
    candidates = []
    for nav in elements:
        if not nav.get("id") or not (nav.get("tag") == "nav" or nav.get("role") == "navigation"):
            continue
        nav_change = changes.get(nav.get("domPath"), {})
        nav_states = [nav_change.get(f"{stage}_visible") for stage in ("desktop", "tablet", "mobile")]
        if nav_states not in ([True, True, False], [True, False, False]):
            continue
        for button in elements:
            if button.get("tag") != "button" or button.get("controls", "").split() != [nav["id"]]:
                continue
            menu_change = changes.get(button.get("domPath"), {})
            menu_states = [menu_change.get(f"{stage}_visible") for stage in ("desktop", "tablet", "mobile")]
            if not all(isinstance(state, bool) and state is not visible
                       for state, visible in zip(menu_states, nav_states)):
                continue
            hidden = nav_change.get("transitions", [])
            shown = menu_change.get("transitions", [])
            if len(hidden) != 1 or len(shown) != 1:
                continue
            fields = ("breakpoint_stage", "breakpoint_lower_bound", "breakpoint_upper_bound")
            if hidden[0].get("change") != "hidden" or shown[0].get("change") != "shown":
                continue
            if any(hidden[0].get(key) != shown[0].get(key) for key in fields):
                continue
            candidates.append({"navigation_path": nav["domPath"], "menu_button_path": button["domPath"],
                               "links": nav.get("links", []),
                               **{key: hidden[0][key] for key in fields}})
    return candidates[0] if len(candidates) == 1 else None
