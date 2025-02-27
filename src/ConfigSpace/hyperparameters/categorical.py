from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Set
from typing_extensions import deprecated, override

import numpy as np

from ConfigSpace.hyperparameters.distributions import (
    Distribution,
    UniformIntegerDistribution,
    WeightedIntegerDiscreteDistribution,
)
from ConfigSpace.hyperparameters.hp_components import Neighborhood, TransformerSeq
from ConfigSpace.hyperparameters.hyperparameter import Hyperparameter
from ConfigSpace.types import Array, f64

if TYPE_CHECKING:
    from ConfigSpace.types import Array

# OPTIM: A lot of categoricals tend to be small, so we cache
# the arange generation, which can be a bit slow for neighbor
# generation, as both halves need to be created and then concatenated.
CACHE_NEIGHBORS_CATEGORICAL_SIZE = 5
"""For sizes smaller than this, we cache the possible neighbors for faster
neighbor generation."""

CACHE_ARANGE_CATEGORICAL_SIZE = 25
"""For sizes smaller than this, we cache the arange for faster neighbor
generation."""


@dataclass
class NeighborhoodCat(Neighborhood):
    """Neighborhood for categorical hyperparameters.

    !!! note

        For
        [`CategoricalHyperparameter`][ConfigSpace.hyperparameters.CategoricalHyperparameter],
        all values are considered equally distant from each other. Thus, the
        possible neighbors is all other values except the current one.
    """

    size: int
    """The number of possible values for the categorical hyperparameter."""

    _cached_arange: Array[f64] | None = None
    _cached_neighbors: list[Array[f64]] | None = None

    def __post_init__(self) -> None:
        if self.size <= CACHE_NEIGHBORS_CATEGORICAL_SIZE:
            _cached_neighbors = []
            for i in range(self.size):
                _range: Array[f64] = np.arange(0, self.size, dtype=f64)
                bot = _range[:i]
                top = _range[i + 1 :]
                choices = np.concatenate((bot, top))
                _cached_neighbors.append(choices)
            self._cached_neighbors = _cached_neighbors
        elif self.size <= CACHE_ARANGE_CATEGORICAL_SIZE:
            self._cached_arange = np.arange(0, self.size, dtype=f64)

    @override
    def __call__(
        self,
        vector: f64,
        n: int,
        *,
        std: float | None = None,
        seed: np.random.RandomState | None = None,
    ) -> Array[f64]:
        seed = np.random.RandomState() if seed is None else seed
        pivot = int(vector)
        if self._cached_neighbors is not None:
            choices = self._cached_neighbors[pivot].copy()
            seed.shuffle(choices)
            return choices

        if self._cached_arange is not None:
            _range = self._cached_arange
        else:
            _range = np.arange(0, self.size, dtype=f64)

        bot = _range[:pivot]
        top = _range[pivot + 1 :]
        choices = np.concatenate((bot, top))
        seed.shuffle(choices)
        return choices[:n]


@dataclass(init=False)
class CategoricalHyperparameter(Hyperparameter[Any, Any]):
    """A hyperparameter that can take on one of a fixed set of values.

    It is assumed there is no inherent order between the choices. If you
    know an order exists, use the
    [`OrdinalHyperparameter`][ConfigSpace.hyperparameters.OrdinalHyperparameter]
    instead.

    The values are sampled uniformly by default, but can be weighted using the
    `weights` parameter. The `weights` parameter is a list of floats, one for
    each choice, that determines the probability of each choice being sampled.
    The probabilities are normalized to sum to 1.
    """

    ORDERABLE: ClassVar[bool] = False

    choices: Sequence[Any]
    """The possible values the hyperparameter can take on."""

    weights: tuple[float, ...] | None
    """The weights of the choices. If `None`, the choices are sampled uniformly."""

    name: str
    """Name of the hyperparameter, with which it can be accessed."""

    default_value: Any
    """The default value of this hyperparameter."""

    meta: Mapping[Hashable, Any] | None
    """Field for holding meta data provided by the user. Not used by ConfigSpace."""

    size: int
    """The number of possible values for the categorical hyperparameter."""

    probabilities: Array[f64] = field(repr=False)

    def __init__(
        self,
        name: str,
        choices: Sequence[Any],
        default_value: Any | None = None,
        meta: Mapping[Hashable, Any] | None = None,
        weights: Sequence[float] | Array[np.number] | None = None,
    ) -> None:
        """Initialize a categorical hyperparameter.

        Args:
            name:
                Name of the hyperparameter, with which it can be accessed.
            choices:
                The possible values the hyperparameter can take on.
            default_value:
                The default value of this hyperparameter. If `None`, the first
                choice is used.
            meta:
                Field for holding meta data provided by the user. Not used by
                ConfigSpace.
            weights:
                The weights of the choices. If `None`, the choices are sampled
                uniformly. If given, the probabilities are normalized to sum to 1.
                The length of the weights has to be the same as the length of the
                choices.
        """
        # TODO: We can allow for None but we need to be sure it doesn't break
        # anything elsewhere.
        if any(choice is None for choice in choices):
            raise TypeError("Choice 'None' is not supported")

        if isinstance(choices, Set):
            raise TypeError(
                "Using a set of choices is prohibited as it can result in "
                "non-deterministic behavior. Please use a list or a tuple.",
            )

        # TODO:For now we assume hashable for choices to make the below check with
        # Counter work. We can probably relax this assumption
        choices = tuple(choices)
        counter = Counter(choices)
        for choice, count in counter.items():
            if count > 1:
                raise ValueError(
                    f"Choices for categorical hyperparameters {name} contain"
                    f" choice `{choice}` {count} times, while only a single oocurence"
                    " is allowed.",
                )

        if isinstance(weights, set):
            raise TypeError(
                "Using a set of weights is prohibited as it can result in "
                "non-deterministic behavior. Please use a list or a tuple.",
            )

        if isinstance(weights, Sequence):
            if len(weights) != len(choices):
                raise ValueError(
                    "The list of weights and the list of choices are required to be"
                    f" of same length. Gave {len(weights)} weights and"
                    f" {len(choices)} choices.",
                )
            if any(weight < 0 for weight in weights):
                raise ValueError(
                    f"Negative weights are not allowed. Got {weights}.",
                )
            if all(weight == 0 for weight in weights):
                raise ValueError(
                    "All weights are zero, at least one weight has to be strictly"
                    " positive.",
                )
            tupled_weights = tuple(weights)
        elif weights is not None:
            raise TypeError(
                f"The weights have to be a list, tuple or None. Got {weights!r}.",
            )
        else:
            tupled_weights = None

        if default_value is not None and default_value not in choices:
            raise ValueError(
                "The default value has to be one of the choices. "
                f"Got {default_value!r} which is not in {choices}.",
            )

        size = len(choices)
        if weights is None:
            probabilities: Array[f64] = np.full(size, fill_value=1 / size, dtype=f64)
        else:
            _weights: Array[f64] = np.asarray(weights, dtype=f64)
            probabilities = _weights / np.sum(_weights)

        if default_value is None and weights is None:
            default_value = choices[0]
        elif default_value is None:
            highest_prob_index = np.argmax(probabilities)
            default_value = choices[highest_prob_index]
        elif default_value in choices:
            pass
        else:
            raise ValueError(f"Illegal default value {default_value}")

        # We only need to pass probabilties is they are non-uniform...
        vector_dist: Distribution
        if weights is not None:
            vector_dist = WeightedIntegerDiscreteDistribution(
                size=size,
                probabilities=np.asarray(probabilities),
            )
        else:
            vector_dist = UniformIntegerDistribution(size=size)

        # NOTE: Unfortunatly, numpy will promote number types to str
        # if there are string types in the array, where we'd rather
        # stick to object type in that case. Hence the manual...
        seq_choices = np.asarray(choices)
        if seq_choices.dtype.kind in {"U", "S"} and not all(
            isinstance(choice, str) for choice in choices
        ):
            seq_choices = np.asarray(choices, dtype=object)

        # We also want to see about value casting, i.e. if our numpy array
        # does not contain objects, then we should include a `value_cast`
        # to transformting `to_value` for a single object type
        if seq_choices.dtype.kind == "b":
            value_cast = bool
        elif seq_choices.dtype.kind in {"i", "u"}:
            value_cast = int
        elif seq_choices.dtype.kind == "f":
            value_cast = float
        elif seq_choices.dtype.kind in {"U", "S"}:
            value_cast = str
        else:
            value_cast = None

        self.probabilities = probabilities
        self.choices = choices
        self.weights = tupled_weights

        super().__init__(
            name=name,
            default_value=default_value,
            vector_dist=vector_dist,
            size=size,
            transformer=TransformerSeq(seq=seq_choices),
            neighborhood=NeighborhoodCat(size=size),
            neighborhood_size=self._categorical_neighborhood_size,
            meta=meta,
            value_cast=value_cast,
        )

    def to_uniform(self) -> CategoricalHyperparameter:
        """Converts this hyperparameter to have uniform weights."""
        return CategoricalHyperparameter(
            name=self.name,
            choices=self.choices,
            weights=None,
            default_value=self.default_value,
            meta=self.meta,
        )

    def __eq__(self, other: Any) -> bool:
        if (
            not isinstance(other, self.__class__)
            or self.name != other.name
            or self.default_value != other.default_value
            or len(self.choices) != len(other.choices)
        ):
            return False

        # Longer check
        for this_choice, this_prob in zip(
            self.choices,
            self.probabilities,
        ):
            if this_choice not in other.choices:
                return False

            index_of_choice_in_other = other.choices.index(this_choice)
            other_prob = other.probabilities[index_of_choice_in_other]
            if this_prob != other_prob:
                return False

        return True

    def _categorical_neighborhood_size(self, value: Any | None) -> int:
        if value is None or value not in self.choices:
            return self.size
        return self.size - 1

    @property
    @deprecated("Please use `len(hp.choices)` or 'hp.size' instead.")
    def num_choices(self) -> int:
        return self.size

    @property
    @deprecated("Please use `.probabilities`. Note, it's a np.ndarray now.")
    def _probabilities(self) -> tuple[float, ...]:
        return tuple(self.probabilities)

    def __str__(self) -> str:
        parts = [
            self.name,
            f"Type: {str(self.__class__.__name__).replace('Hyperparameter', '')}",
            "Choices: {" + ", ".join(map(str, self.choices)) + "}",
            f"Default: {self.default_value}",
        ]
        if not np.all(self.probabilities == self.probabilities[0]):
            parts.append(f"Probabilities: {self.probabilities}")

        return ", ".join(parts)
