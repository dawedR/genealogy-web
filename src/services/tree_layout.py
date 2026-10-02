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
    descendant_partner_gap: float = 24.0
    descendant_union_gap: float = 20.0
    descendant_child_gap: float = 36.0
    descendant_route_gap: float = 12.0
    central_root_exit_offset: float = 40.0
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
            "descendant_partner_gap",
            "descendant_union_gap",
            "descendant_child_gap",
            "descendant_route_gap",
            "central_root_exit_offset",
            "padding",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be zero or greater")
        if self.person_width == 0 or self.person_height == 0:
            raise ValueError("person dimensions must be greater than zero")
        if self.union_vertical_offset > self.generation_gap:
            raise ValueError("union_vertical_offset must fit within generation_gap")
        if self.central_root_exit_offset > self.person_width / 2:
            raise ValueError("central_root_exit_offset must fit within the root card")


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
    """Turn a selected CombinedTree topology into deterministic geometry.

    The central family core is placed first and remains compact. Ancestor and
    descendant envelopes are then measured independently around that fixed G0
    band; their width never changes the position of central partners.
    """

    config = configuration or TreeLayoutConfiguration()
    people = {occurrence.id: occurrence for occurrence in tree.person_occurrences}
    unions = {union.id: union for union in tree.union_occurrences}
    children_by_union: dict[str, list[str]] = {union.id: [] for union in tree.union_occurrences}
    incoming_union_by_child: dict[str, str] = {}
    for link in tree.parent_child_links:
        children_by_union.setdefault(link.union_occurrence_id, []).append(link.child_occurrence_id)
        incoming_union_by_child[link.child_occurrence_id] = link.union_occurrence_id

    core = tree.central_family_core
    core_member_ids = list(core.member_occurrence_ids)
    core_union_ids = list(core.union_occurrence_ids)
    core_member_set = set(core_member_ids)
    core_union_set = set(core_union_ids)
    if core.root_occurrence_id != tree.root_occurrence_id:
        raise ValueError("Tree central core root must match tree root")
    if not core_member_ids or core_member_ids[0] != tree.root_occurrence_id:
        raise ValueError("Tree central core must start with the root occurrence")
    if not set(core_member_ids) <= set(people):
        raise ValueError("Tree central core references unknown person occurrences")
    if not set(core_union_ids) <= set(unions):
        raise ValueError("Tree central core references unknown union occurrences")

    def is_layout_leaf(occurrence: TreePersonOccurrence) -> bool:
        return occurrence.person_id is None or occurrence.cycle_truncated

    def parent_union_for(occurrence_id: str) -> str | None:
        union_id = incoming_union_by_child.get(occurrence_id)
        if union_id is None:
            return None
        union = unions[union_id]
        child = people[occurrence_id]
        return union_id if union.generation < child.generation else None

    def descendant_owner_for(union_id: str) -> str | None:
        union = unions[union_id]
        prefix = "union:"
        suffix = f":family:{union.family_id}"
        if not union.id.startswith(prefix) or not union.id.endswith(suffix):
            return None
        occurrence_id = union.id[len(prefix):-len(suffix)]
        return occurrence_id if occurrence_id in people else None

    def descendant_unions_for(occurrence_id: str) -> list[str]:
        occurrence = people[occurrence_id]
        if is_layout_leaf(occurrence) or occurrence.generation < 0:
            return []
        return [
            union.id
            for union in tree.union_occurrences
            if union.id not in core_union_set
            and union.generation == occurrence.generation
            and descendant_owner_for(union.id) == occurrence_id
        ]

    def merge(target: _MeasuredSubtree, source: _MeasuredSubtree) -> None:
        target.person_x.update(source.person_x)
        target.union_x.update(source.union_x)

    descendant_pivot_by_union = {
        union_id: owner_id
        for union_id in (union.id for union in tree.union_occurrences)
        if union_id not in core_union_set
        and (owner_id := descendant_owner_for(union_id)) is not None
        and people[owner_id].generation >= 0
    }
    vertical_descendant_union_ids = set(descendant_pivot_by_union)

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
        parent_measures = [
            measure_ancestry(partner.occurrence_id)
            for partner in union.partners
        ]
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
        result.width = max(result.width, union_x + config.person_width / 2)
        return result

    def measure_descendancy(occurrence_id: str) -> _MeasuredSubtree:
        """Measure one descendant and independent envelopes for their families.

        Each partner is placed inside their own family envelope below the
        descendant. Consequently, multiple partners do not consume a shared
        horizontal strip to the right of the pivot.
        """

        owned_unions = descendant_unions_for(occurrence_id)
        if not owned_unions:
            root_x = config.person_width / 2
            return _MeasuredSubtree(
                root_occurrence_id=occurrence_id,
                width=config.person_width,
                root_x=root_x,
                person_x={occurrence_id: root_x},
            )

        families: list[tuple[str, list[_MeasuredSubtree], float, float]] = []
        for union_id in owned_unions:
            union = unions[union_id]
            child_measures = [
                measure_descendancy(child_id)
                for child_id in children_by_union.get(union_id, [])
            ]
            children_width = (
                sum(child.width for child in child_measures)
                + config.sibling_gap * max(0, len(child_measures) - 1)
            )
            other_partner_count = sum(
                partner.occurrence_id != occurrence_id
                for partner in union.partners
            )
            partners_width = (
                other_partner_count * config.person_width
                + config.partner_gap * max(0, other_partner_count - 1)
            )
            family_width = max(config.person_width, children_width, partners_width)
            families.append((union_id, child_measures, children_width, family_width))

        total_width = (
            sum(family_width for _, _, _, family_width in families)
            + config.family_gap * (len(families) - 1)
        )
        result = _MeasuredSubtree(
            root_occurrence_id=occurrence_id,
            width=total_width,
            root_x=0.0,
        )

        cursor = 0.0
        family_centers: list[float] = []
        for union_id, child_measures, children_width, family_width in families:
            union = unions[union_id]
            family_center = cursor + family_width / 2
            family_centers.append(family_center)
            result.union_x[union_id] = family_center

            other_partners = [
                partner.occurrence_id
                for partner in union.partners
                if partner.occurrence_id != occurrence_id
            ]
            if other_partners:
                partners_width = (
                    len(other_partners) * config.person_width
                    + config.partner_gap * (len(other_partners) - 1)
                )
                partner_cursor = family_center - partners_width / 2
                for partner_id in other_partners:
                    result.person_x[partner_id] = (
                        partner_cursor + config.person_width / 2
                    )
                    partner_cursor += config.person_width + config.partner_gap

            child_cursor = family_center - children_width / 2
            for child_measure in child_measures:
                merge(result, child_measure.shifted(child_cursor))
                child_cursor += child_measure.width + config.sibling_gap
            cursor += family_width + config.family_gap

        result.root_x = (family_centers[0] + family_centers[-1]) / 2
        result.person_x[occurrence_id] = result.root_x
        return result

    # The central band is intentionally local: broad ancestor or child forests
    # cannot increase the distance between the root and its central partners.
    root_id = tree.root_occurrence_id
    root_x = 0.0
    person_x: dict[str, float] = {root_id: root_x}
    union_x: dict[str, float] = {}
    other_member_ids = core_member_ids[1:]
    if len(other_member_ids) == 1:
        slots = [1]
    else:
        slots = [slot for pair in range(1, len(other_member_ids) + 1) for slot in (-pair, pair)]
        slots = slots[:len(other_member_ids)]
    for occurrence_id, slot in zip(other_member_ids, slots, strict=True):
        person_x[occurrence_id] = root_x + slot * (config.person_width + config.partner_gap)

    for union_id in core_union_ids:
        union = unions[union_id]
        partner_centers = [
            person_x[partner.occurrence_id]
            for partner in union.partners
            if partner.occurrence_id in person_x
        ]
        union_x[union_id] = (
            sum(partner_centers) / len(partner_centers)
            if partner_centers
            else root_x
        )

    core_min_x = min(person_x[item] for item in core_member_ids)
    core_max_x = max(person_x[item] for item in core_member_ids)
    core_center_x = (core_min_x + core_max_x) / 2

    # Pack each actual ancestor envelope independently. The central card itself
    # remains in the fixed band; only its ancestors and parent union are moved.
    ancestry_components = [
        (member_id, measure_ancestry(member_id))
        for member_id in sorted(core_member_ids, key=lambda item: person_x[item])
        if parent_union_for(member_id) is not None and not is_layout_leaf(people[member_id])
    ]
    ancestry_width = sum(component.width for _, component in ancestry_components)
    ancestry_width += config.family_gap * max(0, len(ancestry_components) - 1)
    ancestry_cursor = core_center_x - ancestry_width / 2
    for member_id, component in ancestry_components:
        placed = component.shifted(ancestry_cursor)
        for occurrence_id, x in placed.person_x.items():
            if occurrence_id != member_id:
                person_x[occurrence_id] = x
        union_x.update(placed.union_x)
        ancestry_cursor += component.width + config.family_gap

    # Measure child forests per central union. Each family remains a separate
    # block, packed below the compact core instead of stretching the core band.
    descendant_components: list[list[_MeasuredSubtree]] = []
    for union_id in core_union_ids:
        descendant_components.append(
            [
                measure_descendancy(child_id)
                for child_id in children_by_union.get(union_id, [])
            ]
        )

    group_widths: list[float] = []
    for components in descendant_components:
        if not components:
            group_widths.append(0.0)
            continue
        group_widths.append(
            sum(component.width for component in components)
            + config.sibling_gap * (len(components) - 1)
        )
    nonempty_group_indices = [index for index, width in enumerate(group_widths) if width > 0]
    descendant_width = sum(group_widths[index] for index in nonempty_group_indices)
    descendant_width += config.family_gap * max(0, len(nonempty_group_indices) - 1)
    descendant_cursor = core_center_x - descendant_width / 2
    for index, components in enumerate(descendant_components):
        if not components:
            continue
        for component in components:
            placed = component.shifted(descendant_cursor)
            merge_target = _MeasuredSubtree(root_id, 0, 0, person_x, union_x)
            merge(merge_target, placed)
            descendant_cursor += component.width + config.sibling_gap
        descendant_cursor -= config.sibling_gap
        descendant_cursor += config.family_gap

    # Sibling roots are not central. Keep them deterministic and outside the
    # core band while still allowing their regular descendant branches.
    sibling_root_ids = [
        occurrence.id
        for occurrence in tree.person_occurrences
        if occurrence.generation == 0
        and occurrence.id not in core_member_set
        and parent_union_for(occurrence.id) is not None
    ]
    sibling_cursor = core_max_x + config.person_width + config.family_gap
    for sibling_id in sibling_root_ids:
        placed = measure_descendancy(sibling_id).shifted(sibling_cursor)
        merge_target = _MeasuredSubtree(root_id, 0, 0, person_x, union_x)
        merge(merge_target, placed)
        sibling_cursor += placed.width + config.family_gap

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
    zero_generation_y = config.padding + (-min_generation) * (
        config.person_height + config.generation_gap
    )
    descendant_generation_step = (
        2 * config.person_height
        + config.descendant_partner_gap
        + config.descendant_union_gap
        + config.descendant_child_gap
    )

    def main_person_y(occurrence: TreePersonOccurrence) -> float:
        if occurrence.generation <= 0:
            return config.padding + (
                occurrence.generation - min_generation
            ) * (config.person_height + config.generation_gap)
        return zero_generation_y + (
            config.person_height + config.generation_gap
        ) + (occurrence.generation - 1) * descendant_generation_step

    person_y_by_id = {
        occurrence.id: main_person_y(occurrence)
        for occurrence in tree.person_occurrences
    }
    union_y_by_id: dict[str, float] = {}
    for union_id in sorted(
        vertical_descendant_union_ids,
        key=lambda item: (unions[item].generation, item),
    ):
        union = unions[union_id]
        pivot_id = descendant_pivot_by_union[union_id]
        pivot_y = person_y_by_id[pivot_id]
        for partner in union.partners:
            if partner.occurrence_id != pivot_id:
                person_y_by_id[partner.occurrence_id] = (
                    pivot_y + config.person_height + config.descendant_partner_gap
                )
        union_y = max(
            person_y_by_id[partner.occurrence_id] + config.person_height
            for partner in union.partners
        ) + config.descendant_union_gap
        union_y_by_id[union_id] = union_y
        for child_id in children_by_union.get(union_id, []):
            person_y_by_id[child_id] = union_y + config.descendant_child_gap

    for union in tree.union_occurrences:
        if union.id not in union_y_by_id:
            union_y_by_id[union.id] = (
                person_y_by_id[union.partners[0].occurrence_id]
                + config.person_height
                + config.union_vertical_offset
            )

    person_nodes = tuple(
        PersonLayoutNode(
            occurrence_id=occurrence.id,
            x=person_x[occurrence.id] + x_offset - config.person_width / 2,
            y=person_y_by_id[occurrence.id],
            width=config.person_width,
            height=config.person_height,
        )
        for occurrence in tree.person_occurrences
    )
    person_nodes_by_id = {node.occurrence_id: node for node in person_nodes}
    central_convention_union_ids = (
        set(core_union_ids) if len(core_union_ids) <= 2 else set()
    )
    central_bar_y_by_union: dict[str, float] = {}
    central_root_exit_x_by_union: dict[str, float] = {}
    if central_convention_union_ids:
        root_node = person_nodes_by_id[root_id]
        root_center_x = root_node.x + root_node.width / 2
        couple_y = max(
            person_nodes_by_id[partner.occurrence_id].y + config.person_height
            for union_id in core_union_ids
            for partner in unions[union_id].partners
        ) + config.union_vertical_offset
        for union_id in core_union_ids:
            central_bar_y_by_union[union_id] = couple_y
        if len(core_union_ids) == 1:
            central_root_exit_x_by_union[core_union_ids[0]] = root_center_x
        elif len(core_union_ids) == 2:
            left_union_id, right_union_id = sorted(
                core_union_ids,
                key=lambda union_id: union_x[union_id],
            )
            central_root_exit_x_by_union[left_union_id] = (
                root_center_x - config.central_root_exit_offset
            )
            central_root_exit_x_by_union[right_union_id] = (
                root_center_x + config.central_root_exit_offset
            )

    union_nodes = tuple(
        UnionLayoutNode(
            union_occurrence_id=union.id,
            x=union_x[union.id] + x_offset,
            y=(
                central_bar_y_by_union[union.id]
                if union.id in central_convention_union_ids
                else (
                    person_y_by_id[descendant_pivot_by_union[union.id]]
                    + config.person_height
                    + config.descendant_partner_gap / 2
                    if union.id in vertical_descendant_union_ids
                    else union_y_by_id[union.id]
                )
            ),
        )
        for union in tree.union_occurrences
    )
    union_nodes_by_id = {node.union_occurrence_id: node for node in union_nodes}
    central_descendant_drop_x_by_union: dict[str, float] = {}
    for union_id in central_convention_union_ids:
        root_anchor_x = central_root_exit_x_by_union[union_id]
        other_partner_anchor_xs = [
            person_nodes_by_id[partner.occurrence_id].x
            + person_nodes_by_id[partner.occurrence_id].width / 2
            for partner in unions[union_id].partners
            if partner.occurrence_id != root_id
        ]
        central_descendant_drop_x_by_union[union_id] = (
            (root_anchor_x + other_partner_anchor_xs[0]) / 2
            if other_partner_anchor_xs
            else root_anchor_x
        )

    # Reserve deterministic tracks for unions that preserve the horizontal
    # central/ancestral grammar. Descendant unions use their own vertical
    # family envelopes below.
    unions_by_partner: dict[str, list[str]] = {}
    for union in tree.union_occurrences:
        for partner in union.partners:
            unions_by_partner.setdefault(partner.occurrence_id, []).append(union.id)
    vertical_unions_by_pivot: dict[str, list[str]] = {}
    for union_id, pivot_id in descendant_pivot_by_union.items():
        vertical_unions_by_pivot.setdefault(pivot_id, []).append(union_id)

    edges: list[LayoutEdge] = []
    for union in tree.union_occurrences:
        union_node = union_nodes_by_id[union.id]
        if union.id in central_convention_union_ids:
            for partner in union.partners:
                person_node = person_nodes_by_id[partner.occurrence_id]
                person_center_x = person_node.x + person_node.width / 2
                person_bottom_y = person_node.y + person_node.height
                start_x = (
                    central_root_exit_x_by_union[union.id]
                    if partner.occurrence_id == root_id
                    else person_center_x
                )
                if start_x == union_node.x:
                    points = (
                        LayoutPoint(start_x, person_bottom_y),
                        LayoutPoint(union_node.x, union_node.y),
                    )
                else:
                    points = (
                        LayoutPoint(start_x, person_bottom_y),
                        LayoutPoint(start_x, union_node.y),
                        LayoutPoint(union_node.x, union_node.y),
                    )
                edges.append(
                    LayoutEdge(
                        kind=LayoutEdgeKind.PARTNER,
                        union_occurrence_id=union.id,
                        person_occurrence_id=partner.occurrence_id,
                        points=points,
                    )
                )
        elif union.id in vertical_descendant_union_ids:
            pivot_id = descendant_pivot_by_union[union.id]
            other_partner_nodes = [
                person_nodes_by_id[partner.occurrence_id]
                for partner in union.partners
                if partner.occurrence_id != pivot_id
            ]

            for partner in union.partners:
                person_node = person_nodes_by_id[partner.occurrence_id]
                person_center_x = person_node.x + person_node.width / 2
                if partner.occurrence_id == pivot_id:
                    person_bottom_y = person_node.y + person_node.height
                    if person_center_x == union_node.x:
                        points = (
                            LayoutPoint(person_center_x, person_bottom_y),
                            LayoutPoint(union_node.x, union_node.y),
                        )
                    else:
                        points = (
                            LayoutPoint(person_center_x, person_bottom_y),
                            LayoutPoint(person_center_x, union_node.y),
                            LayoutPoint(union_node.x, union_node.y),
                        )
                elif person_center_x == union_node.x:
                    points = (
                        LayoutPoint(union_node.x, union_node.y),
                        LayoutPoint(person_center_x, person_node.y),
                    )
                else:
                    points = (
                        LayoutPoint(union_node.x, union_node.y),
                        LayoutPoint(person_center_x, union_node.y),
                        LayoutPoint(person_center_x, person_node.y),
                    )
                edges.append(
                    LayoutEdge(
                        kind=LayoutEdgeKind.PARTNER,
                        union_occurrence_id=union.id,
                        person_occurrence_id=partner.occurrence_id,
                        points=points,
                    )
                )
        else:
            shared_partner = max(
                union.partners,
                key=lambda partner: len(unions_by_partner[partner.occurrence_id]),
            )
            shared_unions = unions_by_partner[shared_partner.occurrence_id]
            track_index = shared_unions.index(union.id) + 1
            track_count = len(shared_unions) + 1
            for partner in union.partners:
                person_node = person_nodes_by_id[partner.occurrence_id]
                person_center_x = person_node.x + person_node.width / 2
                person_bottom_y = person_node.y + person_node.height
                if person_center_x == union_node.x:
                    points = (
                        LayoutPoint(person_center_x, person_bottom_y),
                        LayoutPoint(union_node.x, union_node.y),
                    )
                else:
                    track_y = person_bottom_y + (
                        union_node.y - person_bottom_y
                    ) * track_index / track_count
                    points = (
                        LayoutPoint(person_center_x, person_bottom_y),
                        LayoutPoint(person_center_x, track_y),
                        LayoutPoint(union_node.x, track_y),
                        LayoutPoint(union_node.x, union_node.y),
                    )
                edges.append(
                    LayoutEdge(
                        kind=LayoutEdgeKind.PARTNER,
                        union_occurrence_id=union.id,
                        person_occurrence_id=partner.occurrence_id,
                        points=points,
                    )
                )

        child_ids = children_by_union.get(union.id, [])
        if union.id in vertical_descendant_union_ids:
            child_origin = (
                other_partner_nodes[0]
                if other_partner_nodes
                else person_nodes_by_id[descendant_pivot_by_union[union.id]]
            )
            child_origin_x = child_origin.x + child_origin.width / 2
            child_origin_y = child_origin.y + child_origin.height
        elif union.id in central_convention_union_ids:
            child_origin_x = central_descendant_drop_x_by_union[union.id]
            child_origin_y = union_node.y
        else:
            child_origin_x = union_node.x
            child_origin_y = union_node.y
        if child_ids:
            bus_y = (
                child_origin_y
                + min(person_nodes_by_id[child_id].y for child_id in child_ids)
            ) / 2
        for child_id in child_ids:
            child_node = person_nodes_by_id[child_id]
            child_center_x = child_node.x + child_node.width / 2
            if child_center_x == child_origin_x and len(child_ids) == 1:
                points = (
                    LayoutPoint(child_origin_x, child_origin_y),
                    LayoutPoint(child_center_x, child_node.y),
                )
            elif child_center_x == child_origin_x:
                points = (
                    LayoutPoint(child_origin_x, child_origin_y),
                    LayoutPoint(child_origin_x, bus_y),
                    LayoutPoint(child_center_x, child_node.y),
                )
            else:
                points = (
                    LayoutPoint(child_origin_x, child_origin_y),
                    LayoutPoint(child_origin_x, bus_y),
                    LayoutPoint(child_center_x, bus_y),
                    LayoutPoint(child_center_x, child_node.y),
                )
            edges.append(
                LayoutEdge(
                    kind=LayoutEdgeKind.PARENT_CHILD,
                    union_occurrence_id=union.id,
                    person_occurrence_id=child_id,
                    points=points,
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
