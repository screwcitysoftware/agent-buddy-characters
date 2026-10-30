const formatBytes = value => {
  const mib = value / (1024 * 1024);
  return `${mib.toFixed(2)} MiB`;
};

const escapeHtml = value => String(value).replace(/[&<>'"]/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
})[character]);

async function loadCharacters() {
  const container = document.getElementById('characters');
  try {
    const response = await fetch('catalog.json');
    if (!response.ok) throw new Error(`Catalog returned ${response.status}`);
    const catalog = await response.json();
    container.innerHTML = catalog.characters.map(character => `
      <article class="card">
        <div class="preview-wrap">
          <img src="${escapeHtml(character.previewUrl)}" alt="${escapeHtml(character.name)} animation contact sheet" loading="lazy">
        </div>
        <div class="card__body">
          <div class="card__title-row">
            <h3>${escapeHtml(character.name)}</h3>
            <span class="status">${escapeHtml(character.status)}</span>
          </div>
          <p>${escapeHtml(character.description)}</p>
          <dl>
            <div><dt>Agent Buddy</dt><dd>${escapeHtml(character.minimumAgentBuddyVersion)}+</dd></div>
            <div><dt>Pack size</dt><dd>${formatBytes(character.bytes)}</dd></div>
            <div><dt>License</dt><dd>${escapeHtml(character.artworkLicense)}</dd></div>
          </dl>
          <a class="download" href="${escapeHtml(character.downloadUrl)}" download>Download ${escapeHtml(character.file)}</a>
          <details>
            <summary>SHA-256 checksum</summary>
            <code>${escapeHtml(character.sha256)}</code>
          </details>
        </div>
      </article>
    `).join('');
    document.title = `Agent Buddy Characters · ${catalog.releaseVersion === 'development' ? 'Latest' : `v${catalog.releaseVersion}`}`;
  } catch (error) {
    container.innerHTML = '<p class="error">The character catalog could not be loaded. Downloads remain available from GitHub Releases.</p>';
    console.error(error);
  }
}

loadCharacters();

