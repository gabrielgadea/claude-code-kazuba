"""RL Action definitions and selection logic."""

from typing import Any

from ..core.models import RLAction, RLState


class ActionSelector:
    """Selects and validates actions based on state constraints.

    Some actions may not be valid in certain states (e.g., can't query
    Cipher MCP if it's unavailable).
    """

    def __init__(self) -> None:
        # Actions and their requirements
        self._action_requirements: dict[RLAction, dict[str, Any]] = {
            RLAction.USE_LOCAL_CACHE: {"requires_local_cache": True},
            RLAction.QUERY_CIPHER_MCP: {"requires_cipher": True},
            RLAction.ACTIVATE_SKILL: {},
            RLAction.APPLY_PATTERN: {"requires_local_cache": True},
            RLAction.STORE_LESSON: {},
            RLAction.CONSOLIDATE_PATTERNS: {},
            RLAction.SKIP: {},
        }

    def get_valid_actions(self, state: RLState) -> list[RLAction]:
        """Get list of valid actions for current state.

        Args:
            state: Current RL state

        Returns:
            List of valid actions
        """
        valid_actions: list[RLAction] = []

        for action, requirements in self._action_requirements.items():
            if self._is_action_valid(action, state, requirements):
                valid_actions.append(action)

        return valid_actions

    def _is_action_valid(
        self,
        action: RLAction,
        state: RLState,
        requirements: dict[str, Any],
    ) -> bool:
        """Check if action is valid for state.

        Args:
            action: Action to check
            state: Current state
            requirements: Action requirements

        Returns:
            True if action is valid
        """
        # Check local cache requirement
        if requirements.get("requires_local_cache") and not state.has_local_cache:
            return False

        # Check Cipher MCP requirement
        return not (requirements.get("requires_cipher") and not state.cipher_available)

    def get_action_index(self, action: RLAction) -> int:
        """Get numeric index for action.

        Args:
            action: Action enum value

        Returns:
            Index for Q-table
        """
        return list(RLAction).index(action)

    def get_action_from_index(self, index: int) -> RLAction:
        """Get action from numeric index.

        Args:
            index: Numeric index

        Returns:
            Corresponding RLAction
        """
        return list(RLAction)[index]

    @property
    def action_count(self) -> int:
        """Total number of actions."""
        return len(RLAction)

    def get_action_description(self, action: RLAction) -> str:
        """Get human-readable description of action.

        Args:
            action: Action enum value

        Returns:
            Description string
        """
        descriptions = {
            RLAction.USE_LOCAL_CACHE: "Retrieve patterns from local cache (0 tokens)",
            RLAction.QUERY_CIPHER_MCP: "Query Cipher MCP for semantic search (~800 tokens)",
            RLAction.ACTIVATE_SKILL: "Activate relevant ANTT skill",
            RLAction.APPLY_PATTERN: "Apply matched pattern to current task",
            RLAction.STORE_LESSON: "Store lesson learned in memory",
            RLAction.CONSOLIDATE_PATTERNS: "Consolidate similar patterns",
            RLAction.SKIP: "Skip action (no operation)",
        }
        return descriptions.get(action, action.value)
