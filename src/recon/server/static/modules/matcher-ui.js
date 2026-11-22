/**
 * Recon Multi-Entity Table Matchmaker UI (modules/matcher-ui.js)
 * Visualizes primary/foreign key overlap, join cardinality, and identical table alerts.
 */

export function renderTableMatchmaker(matchData, containerEl) {
  if (!containerEl) return;
  if (!matchData) {
    containerEl.style.display = "none";
    containerEl.innerHTML = "";
    return;
  }

  containerEl.style.display = "block";

  if (matchData.is_identical) {
    containerEl.innerHTML = `
      <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 14px 18px;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 20px;">⚠️</span>
            <div>
              <strong style="color: #f59e0b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;">Identical Duplicate Tables Detected</strong>
              <p style="margin: 3px 0 0 0; font-size: 13px; color: var(--recon-text-secondary);">${matchData.summary_message} (${matchData.identical_reason || ""})</p>
            </div>
          </div>
          <span class="badge badge-warning" style="font-weight: 700; padding: 4px 10px;">REDUNDANT DUPLICATE</span>
        </div>
      </div>
    `;
    return;
  }

  if (matchData.compatible_for_join && matchData.top_join_key) {
    const top = matchData.top_join_key;
    const candidatesHtml = (matchData.candidate_keys || [])
      .map(k => `
        <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 6px; font-size: 12px;">
          <code>${k.table_a_column}</code> ➔ <code>${k.table_b_column}</code>
          <span class="badge badge-indigo" style="font-size: 10px;">${k.cardinality}</span>
          <span style="color: var(--recon-text-muted); font-size: 11px;">(${Math.round(k.confidence * 100)}%)</span>
        </div>
      `)
      .join(" ");

    containerEl.innerHTML = `
      <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 14px 18px;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 8px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 20px;">🔗</span>
            <div>
              <strong style="color: var(--apple-accent-action); font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;">Table Matchmaker: Join Compatible</strong>
              <p style="margin: 3px 0 0 0; font-size: 13px; color: var(--recon-text-secondary);">${matchData.summary_message}</p>
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge badge-indigo" style="font-weight: 700;">Cardinality: ${top.cardinality}</span>
            <span class="badge badge-success" style="font-weight: 700;">Confidence: ${Math.round(top.confidence * 100)}%</span>
            <span class="badge badge-muted" style="font-weight: 700;">Recommended: ${matchData.recommended_join_type} JOIN</span>
          </div>
        </div>
        ${candidatesHtml ? `<div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center;"><span style="font-size: 11px; color: var(--recon-text-muted);">Candidate Keys:</span> ${candidatesHtml}</div>` : ""}
      </div>
    `;
    return;
  }

  containerEl.innerHTML = `
    <div style="background: rgba(100, 116, 139, 0.08); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 14px 18px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 20px;">ℹ️</span>
        <div>
          <strong style="color: var(--recon-text-secondary); font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;">Table Matchmaker</strong>
          <p style="margin: 3px 0 0 0; font-size: 13px; color: var(--recon-text-muted);">${matchData.summary_message}</p>
        </div>
      </div>
    </div>
  `;
}
