const formatBytes = value => {
  const mib = value / (1024 * 1024);
  return `${mib.toFixed(2)} MiB`;
};

const escapeHtml = value => String(value).replace(/[&<>'"]/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
})[character]);

const previewMarkup = character => {
  return `<img src="${escapeHtml(character.previewUrl)}" alt="${escapeHtml(character.name)} character preview" loading="lazy">`;
};

const devicePreviewMarkup = character => {
  const animation = character.animation;
  return `
    <div class="device-shell">
      <div class="device-shell__top" aria-hidden="true">
        <span class="device-camera"></span>
        <span class="device-speaker"></span>
      </div>
      <div class="device-screen">
        <img class="device-fallback" src="${escapeHtml(character.previewUrl)}" alt="" loading="lazy">
        <canvas class="device-animation"
          width="${Number(animation.frameWidth)}" height="${Number(animation.frameHeight)}"
          data-sheet="${escapeHtml(animation.sheetUrl)}"
          data-columns="${Number(animation.columns)}"
          data-frames="${Number(animation.frameCount)}"
          data-fps="${Number(animation.fps)}"
          role="img" aria-label="${escapeHtml(character.name)} animated at native device resolution"></canvas>
      </div>
      <div class="device-shell__footer">
        <span>${escapeHtml(character.name)} · ${Number(animation.frameWidth)} × ${Number(animation.frameHeight)} · ${Number(animation.fps)} FPS</span>
        <button class="device-toggle" type="button" data-character="${escapeHtml(character.name)}"
          aria-label="Pause ${escapeHtml(character.name)} animation" aria-pressed="false">Pause</button>
      </div>
    </div>
  `;
};

function initializeAnimations(root = document) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.querySelectorAll('.device-animation').forEach(canvas => {
    const screen = canvas.closest('.device-screen');
    const shell = canvas.closest('.device-shell');
    const button = shell.querySelector('.device-toggle');
    const context = canvas.getContext('2d');
    const image = new Image();
    const columns = Number(canvas.dataset.columns);
    const frameCount = Number(canvas.dataset.frames);
    const fps = Number(canvas.dataset.fps);
    let frame = 0;
    let paused = reduceMotion;
    let visible = true;
    let request = 0;
    let previous = 0;

    const draw = () => {
      const sourceX = (frame % columns) * canvas.width;
      const sourceY = Math.floor(frame / columns) * canvas.height;
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(
        image, sourceX, sourceY, canvas.width, canvas.height,
        0, 0, canvas.width, canvas.height
      );
    };
    const stop = () => {
      if (request) cancelAnimationFrame(request);
      request = 0;
    };
    const tick = timestamp => {
      request = 0;
      if (paused || !visible) return;
      if (!previous || timestamp - previous >= 1000 / fps) {
        frame = (frame + 1) % frameCount;
        previous = timestamp;
        draw();
      }
      request = requestAnimationFrame(tick);
    };
    const start = () => {
      if (!paused && visible && !request) request = requestAnimationFrame(tick);
    };
    const updateButton = () => {
      const action = paused ? 'Play' : 'Pause';
      button.textContent = action;
      button.setAttribute('aria-label', `${action} ${button.dataset.character} animation`);
      button.setAttribute('aria-pressed', String(paused));
    };

    button.addEventListener('click', () => {
      paused = !paused;
      updateButton();
      if (paused) stop(); else start();
    });
    const observer = new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      if (visible) start(); else stop();
    }, { threshold: 0.1 });
    observer.observe(shell);
    image.addEventListener('load', () => {
      draw();
      screen.classList.add('is-ready');
      updateButton();
      start();
    });
    image.addEventListener('error', () => {
      button.hidden = true;
      canvas.hidden = true;
    });
    image.src = canvas.dataset.sheet;
  });
}

async function loadCharacters() {
  const container = document.getElementById('characters');
  const devicePreview = document.getElementById('device-preview');
  try {
    const response = await fetch('catalog.json');
    if (!response.ok) throw new Error(`Catalog returned ${response.status}`);
    const catalog = await response.json();
    container.innerHTML = catalog.characters.map(character => `
      <article class="card">
        <div class="preview-wrap">
          ${previewMarkup(character)}
        </div>
        <div class="card__body">
          <div class="card__title-row">
            <h3>${escapeHtml(character.name)}</h3>
            <span class="status">${escapeHtml(character.status)}</span>
          </div>
          <p>${escapeHtml(character.description)}</p>
          <dl>
            <div><dt>Version</dt><dd>v${escapeHtml(character.version)}</dd></div>
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
    const animatedCharacter = catalog.characters.find(character => character.animation);
    if (animatedCharacter) {
      devicePreview.innerHTML = devicePreviewMarkup(animatedCharacter);
      initializeAnimations(devicePreview);
    } else {
      devicePreview.innerHTML = '<p class="error">A live device preview is not available yet.</p>';
    }
    document.title = 'Character Packs · Screw City Software';
  } catch (error) {
    container.innerHTML = '<p class="error">The character catalog could not be loaded. Downloads remain available from GitHub Releases.</p>';
    devicePreview.innerHTML = '<p class="error">The live device preview could not be loaded.</p>';
    console.error(error);
  }
}

loadCharacters();

