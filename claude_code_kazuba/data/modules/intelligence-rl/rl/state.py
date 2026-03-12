"""RL State representation and discretization.

Converts task context into discretized state for Q-table lookup.
"""

import hashlib
from datetime import datetime

from ..core.models import ProcessType, RLState, TaskType


class RLStateBuilder:
    """Builder for RL state representation.

    Discretizes continuous features into buckets for Q-table indexing.
    """

    def __init__(self) -> None:
        self._complexity_bins = [0, 2, 4, 6, 8, 10]  # 5 buckets
        self._success_rate_bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]  # 5 buckets

    def build_state(
        self,
        task_type: TaskType,
        process_type: ProcessType = ProcessType.UNKNOWN,
        complexity: float = 0.5,
        has_local_cache: bool = False,
        cipher_available: bool = True,
        recent_success_rate: float = 0.5,
    ) -> RLState:
        """Build discretized RL state.

        Args:
            task_type: Type of ANTT task
            process_type: Type of process
            complexity: Task complexity (0-1)
            has_local_cache: Whether local cache has relevant data
            cipher_available: Whether Cipher MCP is available
            recent_success_rate: Recent success rate (0-1)

        Returns:
            Discretized RLState
        """
        # Discretize complexity to 0-10 scale
        complexity_level = int(complexity * 10)

        # Discretize time of day into 4-hour buckets
        hour = datetime.utcnow().hour
        time_bucket = hour // 4  # 0-5

        # Convert task_type enum to string value for RLState
        task_type_str = task_type.value if isinstance(task_type, TaskType) else str(task_type)

        return RLState(
            task_type=task_type_str,
            process_type=process_type,
            complexity_level=complexity_level,
            has_local_cache=has_local_cache,
            cipher_available=cipher_available,
            recent_success_rate=recent_success_rate,
            time_of_day_bucket=time_bucket,
        )

    def state_to_hash(self, state: RLState) -> str:
        """Convert state to hash for Q-table lookup.

        Args:
            state: RLState object

        Returns:
            Hash string for Q-table key
        """
        # Create deterministic string representation
        state_str = (
            f"{state.task_type}:"
            f"{state.process_type.value}:"
            f"{state.complexity_level}:"
            f"{int(state.has_local_cache)}:"
            f"{int(state.cipher_available)}:"
            f"{int(state.recent_success_rate * 10)}:"
            f"{state.time_of_day_bucket}"
        )

        return hashlib.md5(state_str.encode()).hexdigest()[:16]

    def extract_features(self, state: RLState) -> list[float]:
        """Extract numeric features from state for ML models.

        Args:
            state: RLState object

        Returns:
            List of numeric features
        """
        # One-hot encode task type (handle both str and enum)
        task_type_features = [0.0] * len(TaskType)
        task_type_val = state.task_type
        try:
            task_type_enum = TaskType(task_type_val) if isinstance(task_type_val, str) else task_type_val
            task_type_features[list(TaskType).index(task_type_enum)] = 1.0
        except (ValueError, KeyError):
            # Default to UNKNOWN if not found
            task_type_features[list(TaskType).index(TaskType.UNKNOWN)] = 1.0

        # One-hot encode process type
        process_type_features = [0.0] * len(ProcessType)
        process_type_features[list(ProcessType).index(state.process_type)] = 1.0

        # Numeric features
        numeric_features = [
            state.complexity_level / 10.0,
            float(state.has_local_cache),
            float(state.cipher_available),
            state.recent_success_rate,
            state.time_of_day_bucket / 5.0,
        ]

        return task_type_features + process_type_features + numeric_features

    def get_state_space_size(self) -> dict[str, int]:
        """Get size of each state dimension."""
        return {
            "task_types": len(TaskType),
            "process_types": len(ProcessType),
            "complexity_levels": 11,  # 0-10
            "cache_states": 2,
            "cipher_states": 2,
            "success_rate_buckets": 5,
            "time_buckets": 6,
            "total_combinations": (len(TaskType) * len(ProcessType) * 11 * 2 * 2 * 5 * 6),
        }
