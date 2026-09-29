"""Pure, renderer-independent geometry for a combined family tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.services.combined_tree import CombinedTree, TreePersonOccurrence


@dataclass(frozen=True)
class TreeLayoutConfiguration:
    person_width: float = 160.0
    person_height: float = 72.0
    generation_gap: float = 72.0
    partner_gap: float = 32.0
    sibling_gap: float = 32.0
    family_gap: float = 48.0
    union_vertical_offset: float = 36.0
    padding: float = 40.0

    def __post_init__(self) -> None:
        for name in (
            "person_width",
            "person_height",
            "generation_gap",
            "partner_gap",
            "sibling_gap",
            "family_gap",
            "union_vertical_offset",
            "padding",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be zero or greater")
        if self.person_width == 0 or self.person_height == 0:
            raise ValueError("person dimensions must be greater than zero")
        if self.union_vertical_offset > self.generation_gap:
            raise ValueError("union_vertical_offset must fit within generation_gap")


@dataclass(frozen=True)
class LayoutPoint:
    x: float
    y: float


@dataclass(frozen=True)
class LayoutBounds:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class PersonLayoutNode:
    occurrence_id: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class UnionLayoutNode:
    union_occurrence_id: str
    x: float
    y: float


class LayoutEdgeKind(str, Enum):
    PARTNER = "PARTNER"
    PARENT_CHILD = "PARENT_CHILD"


@dataclass(frozen=True)
class LayoutEdge:
    kind: LayoutEdgeKind
    union_occurrence_id: str
    person_occurrence_id: str
    points: tuple[LayoutPoint, ...]


@dataclass(frozen=True)
class TreeLayout:
    person_nodes: tuple[PersonLayoutNode, ...]
    union_nodes: tuple[UnionLayoutNode, ...]
    edges: tuple[LayoutEdge, ...]
    width: float
    height: float
    bounds: LayoutBounds


@dataclass
class _MeasuredSubtree:
    root_occurrence_id: str
    width: float
    root_x: float
    person_x: dict[str, float] = field(default_factory=dict)
    union_x: dict[str, float] = field(default_factory=dict)

    def shifted(self, offset: float) -> _MeasuredSubtree:
        return _MeasuredSubtree(
            root_occurrence_id=self.root_occurrence_id,
            width=self.width,
            root_x=self.root_x + offset,
            person_x={key: value + offset for key, value in self.person_x.items()},
            union_x={key: value + offset for key, value in self.union_x.items()},
        )


def layout_combined_tree(
    tree: CombinedTree,
    configuration: TreeLayoutConfiguration | None = None,
) -> TreeLayout:
    """Turn an already selected CombinedTree topology into deterministic geometry."""

    config = configuration or TreeLayoutConfiguration()
    people = {occurrence.id: occurrence for occurrence in tree.person_occurrences}
    unions = {union.id: union for union in tree.union_occurrences}
    children_by_union: dict[str, list[str]] = {union.id: [] for union in tree.union_occurrences}
    incoming_union_by_child: dict[str, str] = {}
    for link in tree.parent_child_links:
        children_by_union.setdefault(link.union_occurrence_id, []).append(link.child_occurrence_id)
        incoming_union_by_child[link.child_occurrence_id] = link.union_occurrence_id

    root_id = tree.root_occurrence_id

    def is_layout_leaf(occurrence: TreePersonOccurrence) -> bool:
        return occurrence.person_id is None or occurrence.cycle_truncated

    def parent_union_for(occurrence_id: str) -> str | None:
        union_id = incoming_union_by_child.get(occurrence_id)
        if union_id is None:
            return None
        union = unions[union_id]
        child = people[occurrence_id]
        return union_id if union.generation < child.generation else None

    def descendant_unions_for(occurrence_id: str) -> list[str]:
        occurrence = people[occurrence_id]
        if is_layout_leaf(occurrence):
            return []
        return [
            union.id
            for union in tree.union_occurrences
            if union.generation == occurrence.generation
            and any(partner.occurrence_id == occurrence_id for partner in union.partners)
        ]

    def merge(target: _MeasuredSubtree, source: _MeasuredSubtree) -> None:
        target.person_x.update(source.person_x)
        target.union_x.update(source.union_x)

    def measure_ancestry(occurrence_id: str) -> _MeasuredSubtree:
        parent_union_id = parent_union_for(occurrence_id)
        if parent_union_id is None or is_layout_leaf(people[occurrence_id]):
            return _MeasuredSubtree(
                root_occurrence_id=occurrence_id,
                width=config.person_width,
                root_x=config.person_width / 2,
                person_x={occurrence_id: config.person_width / 2},
            )

        union = unions[parent_union_id]
        parent_ids = [partner.occurrence_id for partner in union.partners]
        parent_measures = [measure_ancestry(parent_id) for parent_id in parent_ids]
        cursor = 0.0
        placed_parents: list[_MeasuredSubtree] = []
        for parent_measure in parent_measures:
            placed = parent_measure.shifted(cursor)
            placed_parents.append(placed)
            cursor += parent_measure.width + config.sibling_gap
        parents_width = cursor - config.sibling_gap if placed_parents else 0.0
        parent_centers = [measure.root_x for measure in placed_parents]
        union_x = (parent_centers[0] + parent_centers[-1]) / 2
        result = _MeasuredSubtree(
            root_occurrence_id=occurrence_id,
            width=max(parents_width, config.person_width),
            root_x=union_x,
            person_x={occurrence_id: union_x},
            union_x={parent_union_id: union_x},
        )
        for parent_measure in placed_parents:
            merge(result, parent_measure)
        result.width = max(
            result.width,
            union_x + config.person_width / 2,
        )
        return result

    def measure_descendancy(occurrence_id: str) -> _MeasuredSubtree:
        """Measure one descendant branch with a local, shared marriage band.

        The person occurrence is represented once. Its partners and union
        points occupy compact slots beside it; child envelopes are packed in a
        separate lower band and therefore do not push spouses outward.
        """

        owned_unions = descendant_unions_for(occurrence_id)
        root_x = config.person_width / 2
        result = _MeasuredSubtree(
            root_occurrence_id=occurrence_id,
            width=config.person_width,
            root_x=root_x,
            person_x={occurrence_id: root_x},
        )

        partner_slot = 0
        pair_right = config.person_width
        for union_id in owned_unions:
            union = unions[union_id]
            other_partners = [
                partner.occurrence_id
                for partner in union.partners
                if partner.occurrence_id != occurrence_id
            ]
            if other_partners:
                first_partner_x: float | None = None
                for partner_id in other_partners:
                    partner_slot += 1
                    partner_x = root_x + partner_slot * (
                        config.person_width + config.partner_gap
                    )
                    result.person_x[partner_id] = partner_x
                    pair_right = max(
                        pair_right,
                        partner_x + config.person_width / 2,
                    )
                    if first_partner_x is None:
                        first_partner_x = partner_x
                result.union_x[union_id] = (root_x + first_partner_x) / 2
            else:
                result.union_x[union_id] = root_x + config.person_width / 2

        child_cursor = 0.0
        for union_id in owned_unions:
            child_measures = [
                measure_descendancy(child_id)
                for child_id in children_by_union.get(union_id, [])
            ]
            for child_measure in child_measures:
                placed = child_measure.shifted(child_cursor)
                merge(result, placed)
                child_cursor += child_measure.width + config.sibling_gap
            if child_measures:
                child_cursor -= config.sibling_gap
                child_cursor += config.family_gap

        children_right = (
            child_cursor - config.family_gap
            if child_cursor > 0
            else 0.0
        )
        result.width = max(pair_right, children_right)
        return result

    ancestry = measure_ancestry(root_id)
    descendant_root_ids = [root_id]
    root_parent_union_id = parent_union_for(root_id)
    if tree.options.show_siblings and root_parent_union_id is not None:
        linked_roots = [
            child_id
            for child_id in children_by_union.get(root_parent_union_id, [])
            if people[child_id].generation == 0
        ]
        if linked_roots:
            descendant_root_ids = linked_roots

    descendant_measures: list[_MeasuredSubtree] = []
    descendant_cursor = 0.0
    for descendant_root_id in descendant_root_ids:
        measure = measure_descendancy(descendant_root_id).shifted(descendant_cursor)
        descendant_measures.append(measure)
        descendant_cursor += measure.width + config.sibling_gap
    descendancy = _MeasuredSubtree(
        root_occurrence_id=root_id,
        width=descendant_cursor - config.sibling_gap,
        root_x=next(
            measure.root_x
            for measure in descendant_measures
            if measure.root_occurrence_id == root_id
        ),
    )
    for measure in descendant_measures:
        merge(descendancy, measure)

    ancestry_offset = descendancy.root_x - ancestry.root_x
    ancestry = ancestry.shifted(ancestry_offset)

    person_x = dict(ancestry.person_x)
    person_x.update(descendancy.person_x)
    union_x = dict(ancestry.union_x)
    union_x.update(descendancy.union_x)

    if set(person_x) != set(people):
        missing = sorted(set(people) - set(person_x))
        raise ValueError(f"Tree layout has unplaced person occurrences: {missing}")
    if set(union_x) != set(unions):
        missing = sorted(set(unions) - set(union_x))
        raise ValueError(f"Tree layout has unplaced union occurrences: {missing}")

    min_x = min(value - config.person_width / 2 for value in person_x.values())
    max_x = max(value + config.person_width / 2 for value in person_x.values())
    x_offset = config.padding - min_x
    min_generation = min(occurrence.generation for occurrence in people.values())

    def person_y(occurrence: TreePersonOccurrence) -> float:
        return config.padding + (
            occurrence.generation - min_generation
        ) * (config.person_height + config.generation_gap)

    person_nodes = tuple(
        PersonLayoutNode(
            occurrence_id=occurrence.id,
            x=person_x[occurrence.id] + x_offset - config.person_width / 2,
            y=person_y(occurrence),
            width=config.person_width,
            height=config.person_height,
        )
        for occurrence in tree.person_occurrences
    )
    person_nodes_by_id = {node.occurrence_id: node for node in person_nodes}
    union_nodes = tuple(
        UnionLayoutNode(
            union_occurrence_id=union.id,
            x=union_x[union.id] + x_offset,
            y=(
                person_y(next(
                    people[partner.occurrence_id]
                    for partner in union.partners
                ))
                + config.person_height
                + config.union_vertical_offset
            ),
        )
        for union in tree.union_occurrences
    )
    union_nodes_by_id = {node.union_occurrence_id: node for node in union_nodes}

    edges: list[LayoutEdge] = []
    for union in tree.union_occurrences:
        union_node = union_nodes_by_id[union.id]
        for partner in union.partners:
            person_node = person_nodes_by_id[partner.occurrence_id]
            edges.append(
                LayoutEdge(
                    kind=LayoutEdgeKind.PARTNER,
                    union_occurrence_id=union.id,
                    person_occurrence_id=partner.occurrence_id,
                    points=(
                        LayoutPoint(person_node.x + person_node.width / 2, person_node.y + person_node.height),
                        LayoutPoint(union_node.x, union_node.y),
                    ),
                )
            )
        for child_id in children_by_union.get(union.id, []):
            child_node = person_nodes_by_id[child_id]
            edges.append(
                LayoutEdge(
                    kind=LayoutEdgeKind.PARENT_CHILD,
                    union_occurrence_id=union.id,
                    person_occurrence_id=child_id,
                    points=(
                        LayoutPoint(union_node.x, union_node.y),
                        LayoutPoint(child_node.x + child_node.width / 2, union_node.y),
                        LayoutPoint(child_node.x + child_node.width / 2, child_node.y),
                    ),
                )
            )

    max_y = max(
        [node.y + node.height for node in person_nodes]
        + [node.y for node in union_nodes]
    )
    width = max_x - min_x + 2 * config.padding
    height = max_y + config.padding
    return TreeLayout(
        person_nodes=person_nodes,
        union_nodes=union_nodes,
        edges=tuple(edges),
        width=width,
        height=height,
        bounds=LayoutBounds(0.0, 0.0, width, height),
    )
