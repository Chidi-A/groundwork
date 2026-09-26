from collections import Counter
from datetime import UTC, datetime

from app.models import Insight, InsightType, Project, ReviewStatus

def _reviewed_count(insights: list[Insight]) -> int:
    reviewed = {ReviewStatus.confirmed, ReviewStatus.edited}
    return sum(1 for i in insights if i.review_status in reviewed)


def build_report_markdown(
    project: Project,
    insights: list[Insight],
    document_count: int,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Executive Summary: {project.name}",
        "",
        f"Generated: {now}",
        f"Insights analyzed: {len(insights)} ({_reviewed_count(insights)} reviewed)",
        f"Documents in project: {document_count}",
        "",
    ]
    if not insights:
        lines.extend([
            "## Overview",
            "",
            "No insights have been extracted for this project yet.",
            "",
        ])
        return "\n".join(lines)
    type_counts = Counter(i.type.value for i in insights)
    theme_counts = Counter(i.theme for i in insights if i.theme)
    sentiment_counts = Counter(i.sentiment.value for i in insights)
    lines.extend([
        "## Overview",
        "",
        f"- **Themes identified:** {len(theme_counts)}",
        f"- **Pain points:** {type_counts.get(InsightType.pain_point.value, 0)}",
        f"- **Opportunities:** {type_counts.get(InsightType.opportunity.value, 0)}",
        f"- **Feature requests:** {type_counts.get(InsightType.feature_request.value, 0)}",
        "",
        "## Insights by type",
        "",
        "| Type | Count |",
        "| --- | ---: |",
    ])
    for insight_type, count in sorted(type_counts.items()):
        lines.append(f"| {insight_type.replace('_', ' ').title()} | {count} |")
    lines.append("")
    if theme_counts:
        lines.extend([
            "## Themes",
            "",
            "| Theme | Count |",
            "| --- | ---: |",
        ])
        for theme, count in theme_counts.most_common():
            lines.append(f"| {theme} | {count} |")
        lines.append("")
    pain_points = [i for i in insights if i.type == InsightType.pain_point]
    if pain_points:
        lines.extend(["## Top pain points", ""])
        for insight in pain_points[:10]:
            theme_label = f" ({insight.theme})" if insight.theme else ""
            lines.append(f"- **{insight.text}**{theme_label}")
            if insight.source_quote:
                loc = f" — {insight.source_location}" if insight.source_location else ""
                lines.append(f'  > "{insight.source_quote}"{loc}')
        lines.append("")
    quotes = [
        i for i in insights
        if i.type == InsightType.quote or i.source_quote
    ]
    if quotes:
        lines.extend(["## Notable quotes", ""])
        seen: set[str] = set()
        for insight in quotes:
            quote_text = insight.source_quote or insight.text
            if quote_text in seen:
                continue
            seen.add(quote_text)
            loc = f" ({insight.source_location})" if insight.source_location else ""
            lines.append(f'- "{quote_text}"{loc}')
            if len(seen) >= 10:
                break
        lines.append("")
    lines.extend([
        "## Sentiment",
        "",
        "| Sentiment | Count |",
        "| --- | ---: |",
    ])
    for sentiment, count in sentiment_counts.most_common():
        lines.append(f"| {sentiment.title()} | {count} |")
    lines.append("")
    return "\n".join(lines)