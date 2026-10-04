import re
from typing import List, Optional


class SelectorSelfHealer:
    """Provides semantic selector healing when web UIs change element IDs or CSS classes."""

    @staticmethod
    def generate_candidate_selectors(field_name: str, element_type: str = "input") -> List[str]:
        """Generates ranked alternative selectors when primary selector fails."""
        normalized = field_name.lower().replace("_", "-").replace(" ", "-")
        plain = field_name.lower().replace("_", "").replace("-", "")

        candidates = [
            # 1. Exact ID match
            f"#{normalized}-input",
            f"#{normalized}",
            f"#{field_name}",
            # 2. Name attribute match
            f"{element_type}[name='{field_name}']",
            f"{element_type}[name='{normalized}']",
            # 3. Aria-label / Placeholder match
            f"{element_type}[placeholder*='{field_name}']",
            f"{element_type}[aria-label*='{field_name}']",
            # 4. Partial substring match on ID
            f"{element_type}[id*='{plain}']",
            # 5. Label sibling relation
            f"//label[contains(text(), '{field_name}')]/following::{element_type}[1]",
        ]
        return candidates

    @staticmethod
    async def heal_and_locate(page, field_name: str, preferred_selector: str, element_type: str = "input") -> Optional[str]:
        """Attempts to find the element using preferred selector, falls back to candidates."""
        try:
            loc = page.locator(preferred_selector)
            if await loc.count() > 0 and await loc.first.is_visible():
                return preferred_selector
        except Exception:
            pass

        # Primary failed, attempt self-healing across candidates
        candidates = SelectorSelfHealer.generate_candidate_selectors(field_name, element_type)
        for cand in candidates:
            try:
                cand_loc = page.locator(cand)
                if await cand_loc.count() > 0 and await cand_loc.first.is_visible():
                    return cand
            except Exception:
                continue

        return None
