import {
    historicalProposalLabel,
    historicalReasonLabel,
    historicalReliabilityLabel,
    historicalWarningLabel,
} from "./place_formatters.js";

export function historicalProposalKey(proposal) {
    return `${proposal.source_original_name}\u0000${proposal.historical_original_name}`;
}

export function historicalProposalsForEntry(entry, skipped, showSkipped) {
    const proposals = entry.historical_reconciliation?.proposals || [];
    return proposals.filter(proposal =>
        showSkipped || !skipped.has(historicalProposalKey(proposal)),
    );
}

export function renderHistoricalProposals({
    entry, skipped, showSkipped, onReuse, onSkip, onRestore, onToggleSkipped,
    onPreview, onSearchAlternative,
}) {
    const reconciliation = entry.historical_reconciliation;
    if (!reconciliation?.proposals.length) return null;

    const section = document.createElement("div");
    section.className = "places-workbench-historical";
    const heading = document.createElement("h4");
    heading.textContent = "Réconciliation historique";
    section.appendChild(heading);

    const skippedCount = reconciliation.proposals.filter(proposal =>
        skipped.has(historicalProposalKey(proposal)),
    ).length;
    if (skippedCount > 0) {
        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.textContent = showSkipped
            ? "Masquer les propositions passées"
            : `Revoir les propositions passées (${skippedCount})`;
        toggle.addEventListener("click", onToggleSkipped);
        section.appendChild(toggle);
    }

    const proposals = historicalProposalsForEntry(entry, skipped, showSkipped);
    if (!proposals.length) {
        const message = document.createElement("p");
        message.textContent = "Toutes les propositions ont été passées pour cette session.";
        section.appendChild(message);
        return section;
    }
    for (const proposal of proposals) {
        section.appendChild(proposalElement(
            proposal,
            skipped.has(historicalProposalKey(proposal)),
            {onReuse, onSkip, onRestore, onPreview, onSearchAlternative},
        ));
    }
    return section;
}

function proposalElement(proposal, isSkipped, {
    onReuse, onSkip, onRestore, onPreview, onSearchAlternative,
}) {
    const article = document.createElement("article");
    article.className = "places-workbench-historical-proposal" +
        (proposal.classification === "REVIEW" ? " is-review" : "");
    article.append(
        paragraph("Ancien libellé", proposal.historical_original_name),
        paragraph("Statut historique", proposal.historical_status),
        paragraph("Nom normalisé", proposal.historical_normalized_name || "Non renseigné"),
        paragraph(
            "Similarité documentaire",
            `${proposal.score} / 100 — ${historicalProposalLabel(proposal.classification)}`,
        ),
        paragraph(
            "Fiabilité des coordonnées",
            historicalReliabilityLabel(proposal.coordinate_reuse_reliability),
        ),
        paragraph("Raisons", proposal.reasons.map(historicalReasonLabel).join(" · ") || "Aucune"),
    );
    if (proposal.historical_status === "VALIDATED") {
        article.appendChild(paragraph("Origine", "Validation géographique antérieure"));
    }
    if (proposal.warnings.length) {
        const warning = paragraph(
            "À vérifier",
            proposal.warnings.map(historicalWarningLabel).join(" · "),
        );
        warning.classList.add("places-workbench-historical-warnings");
        article.appendChild(warning);
    }
    const actions = document.createElement("div");
    actions.className = "places-workbench-historical-actions";
    if (isSkipped) {
        const restore = button("Réafficher", () => onRestore(proposal));
        actions.appendChild(restore);
    } else {
        if (proposal.latitude !== null && proposal.longitude !== null) {
            actions.appendChild(button("Voir sur la carte", () => onPreview(proposal)));
        }
        const reuse = button("Reprendre cette position", () => onReuse(proposal));
        reuse.disabled = !["STRONG_MATCH", "REVIEW"].includes(proposal.classification);
        const skip = button("Passer", () => onSkip(proposal));
        actions.append(reuse, skip);
        if (proposal.latitude !== null && proposal.longitude !== null) {
            const question = document.createElement("p");
            question.textContent = "Cette position correspond-elle au lieu de ton GEDCOM ?";
            article.appendChild(question);
            actions.appendChild(button("Rechercher une autre position", onSearchAlternative));
        }
    }
    article.appendChild(actions);
    return article;
}

function paragraph(label, value) {
    const element = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = `${label} : `;
    element.append(strong, document.createTextNode(value));
    return element;
}

function button(label, handler) {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = label;
    element.addEventListener("click", handler);
    return element;
}
