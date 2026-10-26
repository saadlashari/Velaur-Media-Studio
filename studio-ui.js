

    const API_HOST = window.location.origin;
    let currentMode = 'link';
    let selectedLocalFile = null;
    let selectedFormat = 'mp4';
    let selectedResolution = '1080';
    let totalVideoDuration = 0;
    let currentLoadedUrl = '';
    let localObjectUrl = null;
    let previewController = null;
    let previewMode = '';
    let automaticFallbackUsed = false;
    let exportBusy = false;
    let rangeInitialized = false;
    const videoPlayer = document.getElementById('mainVideoPlayer');
    const startSlider = document.getElementById('startSlider');
    const endSlider = document.getElementById('endSlider');
    const previewStatus = document.getElementById('previewStatus');
    const exportStatus = document.getElementById('exportStatus');
    const saveLink = document.getElementById('saveLink');
    const compatibleBtn = document.getElementById('compatiblePreviewBtn');

    function statusText(element, text, error = false) {
      element.textContent = text;
      element.classList.toggle('text-red-600', error);
      element.setAttribute('role', error ? 'alert' : 'status');
      window.dispatchEvent(new CustomEvent('velaur:limit-status',{detail:{id:element.id,text,error}}));
    }

    function detailMessage(payload, fallback) {
      if (typeof payload.detail === 'string') return payload.detail;
      if (Array.isArray(payload.detail)) return payload.detail.map(x => x.msg || 'Invalid input').join('; ');
      return payload.error || fallback;
    }

    async function api(path, options = {}) {
      const {signal, ...rest} = options;
      if (options.method && !['GET','HEAD'].includes(options.method)) {
        await window.VelaurAccount.ready;
        rest.headers = {...rest.headers, 'X-CSRF-Token': window.VelaurAccount.csrf};
      }
      const requestTimeout = AbortSignal.timeout(25000);
      const response = await fetch(API_HOST + path, {
        cache: 'no-store', ...rest,
        signal: signal ? AbortSignal.any([signal, requestTimeout]) : requestTimeout
      });
      const text = await response.text();
      let payload;
      try { payload = JSON.parse(text); }
      catch { throw new Error('Server returned HTTP ' + response.status + '. Please retry.'); }
      if (!response.ok) throw new Error(detailMessage(payload, 'Server error (' + response.status + ').'));
      return payload;
    }

    function delay(ms, signal) {
      return new Promise((resolve, reject) => {
        if (signal?.aborted) return reject(signal.reason);
        const stop = () => { clearTimeout(timer); reject(signal.reason); };
        const timer = setTimeout(() => {
          signal?.removeEventListener('abort', stop);
          resolve();
        }, ms);
        signal?.addEventListener('abort', stop, {once: true});
      });
    }

    function jobDescription(job, started) {
      const elapsed = Math.max(0, Math.floor((Date.now() - started) / 1000));
      const percent = typeof job.percent === 'number' && job.state !== 'done'
        ? ' · ' + Math.round(job.percent) + '%' : '';
      const speed = job.speed && job.stage === 'Downloading source'
        ? ' · ' + (job.speed / 1048576).toFixed(1) + ' MB/s' : '';
      return (job.stage || 'Processing') + percent + speed + ' · ' + elapsed + 's';
    }

    async function watchJob(job, update, signal) {
      const started = Date.now();
      let failures = 0;
      while (true) {
        update(job, started);
        if (job.state === 'done') return job.result;
        if (job.state === 'error') throw new Error(job.error || 'Media processing failed.');
        await delay(1000, signal);
        try {
          job = await api('/api/jobs/' + encodeURIComponent(job.id), {signal});
          failures = 0;
        } catch (error) {
          if (signal?.aborted) throw error;
          // Only transient connection failures are retried. Explicit server errors surface.
          if (!(error instanceof TypeError) && error.name !== 'TimeoutError') throw error;
          if (++failures >= 4) throw new Error('Connection interrupted. Reload this page to resume checking your export.');
          await delay(1500, signal);
        }
      }
    }

    function resetPreview() {
      previewController?.abort();
      previewController = null;
      document.getElementById('previewBtn').disabled = false;
      document.getElementById('previewBtn').innerHTML = uiIcon('play') + '<span>Preview</span>';
      currentLoadedUrl = '';
      previewMode = '';
      automaticFallbackUsed = false;
      rangeInitialized = false;
      totalVideoDuration = 0;
      startSlider.value = 0;
      endSlider.value = 0;
      startSlider.disabled = true;
      endSlider.disabled = true;
      videoPlayer.pause();
      videoPlayer.removeAttribute('src');
      videoPlayer.removeAttribute('poster');
      videoPlayer.load();
      document.getElementById('previewCard').classList.add('hidden');
      document.getElementById('totalDurationBadge').textContent = '00:00:00';
      compatibleBtn.classList.add('hidden');
      statusText(previewStatus, '');
    }

    function switchMode(mode) {
      resetPreview();
      currentMode = mode;
      document.getElementById('linkContainer').classList.toggle('hidden', mode !== 'link');
      document.getElementById('uploadContainer').classList.toggle('hidden', mode !== 'upload');
      for (const [id, active] of [['tabLinkBtn', mode === 'link'], ['tabUploadBtn', mode === 'upload']]) {
        document.getElementById(id).className =
          'flex-1 sm:flex-none px-4 py-2 rounded-xl text-xs font-semibold border transition ' +
          (active ? 'bg-slate-900 text-white border-slate-900' : 'bg-slate-100 text-slate-600 border-slate-200');
      }
      document.getElementById('tabLinkBtn').setAttribute('aria-pressed', mode === 'link');
      document.getElementById('tabUploadBtn').setAttribute('aria-pressed', mode === 'upload');
      if (mode === 'upload' && selectedLocalFile) showLocalPreview();
    }

    function showLocalPreview() {
      if (localObjectUrl) URL.revokeObjectURL(localObjectUrl);
      localObjectUrl = URL.createObjectURL(selectedLocalFile);
      document.getElementById('videoTitleDisplay').textContent = selectedLocalFile.name;
      videoPlayer.src = localObjectUrl;
      videoPlayer.load();
      document.getElementById('previewCard').classList.remove('hidden');
      statusText(previewStatus, 'Loading local preview...');
    }

    function handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      resetPreview();
      selectedLocalFile = file;
      document.getElementById('uploadBoxTitle').textContent =
        'Selected: ' + file.name + ' (' + (file.size / 1048576).toFixed(1) + ' MB)';
      showLocalPreview();
    }

    function formatSeconds(seconds) {
      seconds = Math.max(0, Math.floor(Number(seconds) || 0));
      return [Math.floor(seconds / 3600), Math.floor(seconds % 3600 / 60), seconds % 60]
        .map(x => String(x).padStart(2, '0')).join(':');
    }

    function applyVideoDuration(duration) {
      if (!Number.isFinite(Number(duration)) || Number(duration) <= 0) return;
      const dur = Math.max(1, Math.floor(Number(duration)));
      const start = rangeInitialized ? Math.min(Number(startSlider.value), dur - 1) : 0;
      const end = rangeInitialized ? Math.min(Math.max(Number(endSlider.value), start + 1), dur) : dur;
      totalVideoDuration = dur;
      startSlider.max = dur;
      endSlider.max = dur;
      startSlider.value = start;
      endSlider.value = end;
      startSlider.disabled = false;
      endSlider.disabled = false;
      rangeInitialized = true;
      document.getElementById('totalDurationBadge').textContent = formatSeconds(dur);
      updateSliderDisplay();
    }

    videoPlayer.addEventListener('loadedmetadata', () => applyVideoDuration(videoPlayer.duration));
    videoPlayer.addEventListener('durationchange', () => applyVideoDuration(videoPlayer.duration));
    videoPlayer.addEventListener('canplay', () => {
      statusText(previewStatus, 'Preview ready.');
      compatibleBtn.classList.add('hidden');
    });
    videoPlayer.addEventListener('waiting', () => {
      if (videoPlayer.getAttribute('src')) statusText(previewStatus, 'Buffering preview...');
    });
    videoPlayer.addEventListener('error', () => {
      if (!videoPlayer.getAttribute('src')) return;
      if (currentMode === 'link' && previewMode === 'stream' && !automaticFallbackUsed) {
        automaticFallbackUsed = true;
        loadVideo(true);
        return;
      }
      statusText(previewStatus, 'Preview could not play. You can still export the video, or retry the preview.', true);
      if (currentMode === 'link') compatibleBtn.classList.remove('hidden');
    });

    async function loadVideo(forceDownload = false) {
      const url = document.getElementById('mediaUrl').value.trim();
      try {
        const parsed = new URL(url);
        if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error();
      } catch { statusText(previewStatus, 'Enter a valid video link first.', true); return; }
      if (!forceDownload) resetPreview();
      previewController?.abort();
      const controller = new AbortController();
      previewController = controller;
      const previewBtn = document.getElementById('previewBtn');
      previewBtn.disabled = true;
      previewBtn.innerHTML = uiIcon('loader') + '<span>Loading...</span>';
      compatibleBtn.classList.add('hidden');
      statusText(previewStatus, forceDownload ? 'Preparing a compatible preview...' : 'Reading video information...');
      try {
        const job = await api('/api/jobs/preview', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url, force_download: forceDownload}), signal: controller.signal
        });
        const result = await watchJob(job, (state, started) => {
          statusText(previewStatus, jobDescription(state, started));
          if (state.media) {
            currentLoadedUrl = url;
            document.getElementById('videoTitleDisplay').textContent = state.media.title || 'Video';
            applyVideoDuration(state.media.duration);
            document.getElementById('previewCard').classList.remove('hidden');
          }
        }, controller.signal);
        if (controller.signal.aborted) return;
        currentLoadedUrl = url;
        previewMode = result.preview_mode;
        document.getElementById('videoTitleDisplay').textContent = result.title || 'Video';
        applyVideoDuration(result.duration);
        if (result.thumbnail) videoPlayer.poster = result.thumbnail;
        if (!result.stream_url) throw new Error('No playable preview was returned. Try exporting instead.');
        // Never substitute a YouTube/TikTok webpage for a media source.
        const source = new URL(result.stream_url, API_HOST);
        if (source.origin !== API_HOST) throw new Error('Preview must be served by this media server.');
        videoPlayer.src = source.href;
        videoPlayer.load();
        document.getElementById('previewCard').classList.remove('hidden');
        statusText(previewStatus, 'Loading video playback...');
      } catch (error) {
        if (!controller.signal.aborted) {
          statusText(previewStatus, error.name === 'TimeoutError' ? 'Server connection timed out. Please retry.' : error.message, true);
          compatibleBtn.classList.remove('hidden');
        }
      } finally {
        if (previewController === controller) {
          previewBtn.disabled = false;
          previewBtn.innerHTML = uiIcon('play') + '<span>Preview</span>';
        }
      }
    }

    function handleRangeChange(changed) {
      const start = Number(startSlider.value);
      const end = Number(endSlider.value);
      if (changed === 'start' && start >= end) startSlider.value = Math.max(0, end - 1);
      if (changed === 'end' && end <= start) endSlider.value = Math.min(totalVideoDuration, start + 1);
      if (videoPlayer.readyState >= 1) {
        videoPlayer.currentTime = Number(changed === 'start' ? startSlider.value : endSlider.value);
      }
      updateSliderDisplay();
    }

    function updateSliderDisplay() {
      document.getElementById('startDisplay').textContent = formatSeconds(startSlider.value);
      document.getElementById('endDisplay').textContent = formatSeconds(endSlider.value);
      document.getElementById('clipLengthText').textContent =
        'Clip: ' + formatSeconds(Number(endSlider.value) - Number(startSlider.value));
    }

    function setFormat(format) {
      selectedFormat = format;
      document.getElementById('resolutionGroup').classList.toggle('hidden', format === 'mp3');
      for (const [id, active] of [['btnFmtMp4', format === 'mp4'], ['btnFmtMp3', format === 'mp3']]) {
        document.getElementById(id).className = 'py-2.5 px-3 rounded-xl text-xs font-semibold border transition ' +
          (active ? 'border-cyan-500 bg-cyan-50 text-cyan-800' : 'border-slate-200 bg-slate-50 text-slate-600');
      }
      document.getElementById('qualitySelect').innerHTML = format === 'mp3'
        ? '<option value="high">320 kbps</option><option value="standard">192 kbps</option><option value="low">128 kbps</option>'
        : '<option value="high">High (recommended)</option><option value="max">Maximum</option><option value="standard">Smaller file</option>';
      updateExportSummary();
    }

    function setResolution(resolution) {
      selectedResolution = resolution;
      for (const value of ['720', '1080', '2160']) {
        document.getElementById('res' + value).className = 'py-2 rounded-xl text-xs font-medium border transition ' +
          (value === resolution ? 'border-cyan-500 bg-cyan-50 text-cyan-800' : 'border-slate-200 bg-slate-50 text-slate-600');
      }
      updateExportSummary();
    }

    function setExportBusy(busy) {
      exportBusy = busy;
      document.getElementById('exportBtn').disabled = busy;
      document.getElementById('exportBtn').classList.toggle('opacity-60', busy);
      document.getElementById('exportIcon').className = 'button-icon';
      document.getElementById('exportIcon').innerHTML = uiIcon(busy ? 'loader' : 'download');
      document.getElementById('exportText').textContent = busy ? 'Processing...' : 'Export media';
    }

    function rememberJob(id) { try { localStorage.setItem('velaurExportJobV3', id); } catch {} }
    function forgetJob() { try { localStorage.removeItem('velaurExportJobV3'); } catch {} }

    async function finishExport(job) {
      rememberJob(job.id);
      const result = await watchJob(job, (state, started) => {
        document.getElementById('exportText').textContent = state.stage || 'Processing...';
        statusText(exportStatus, jobDescription(state, started));
        const progress = document.getElementById('exportProgress');
        progress.classList.remove('hidden');
        if (typeof state.percent === 'number') progress.value = state.percent;
        else progress.removeAttribute('value');
      });
      saveLink.href = result.download_url;
      saveLink.download = result.filename;
      saveLink.textContent = 'Save ' + result.filename;
      saveLink.classList.remove('hidden');
      statusText(exportStatus, 'File ready. Your browser download has been requested. Use the Save link if it does not start.');
      forgetJob();
      saveLink.click();
    }

    function uploadJob(formData) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', API_HOST + '/api/upload-export');
        xhr.setRequestHeader('X-CSRF-Token', window.VelaurAccount.csrf);
        xhr.timeout = 60 * 60 * 1000;
        xhr.upload.onprogress = event => {
          const percent = event.lengthComputable ? Math.round(event.loaded / event.total * 100) : null;
          statusText(exportStatus, percent === 100 ? 'Upload sent. Waiting for server...' :
            'Uploading file' + (percent === null ? '...' : ' · ' + percent + '%'));
        };
        xhr.onerror = () => reject(new Error('Upload connection failed. Please retry.'));
        xhr.ontimeout = () => reject(new Error('Upload timed out. Try a smaller file.'));
        xhr.onload = () => {
          let result;
          try { result = JSON.parse(xhr.responseText); }
          catch { reject(new Error('Upload failed (HTTP ' + xhr.status + ').')); return; }
          if (xhr.status >= 200 && xhr.status < 300) resolve(result);
          else reject(new Error(detailMessage(result, 'Upload failed (HTTP ' + xhr.status + ').')));
        };
        xhr.send(formData);
      });
    }

    async function triggerExport() {
      if (exportBusy) return;
      const mode = currentMode;
      const url = document.getElementById('mediaUrl').value.trim();
      if (mode === 'link' && !url) return statusText(exportStatus, 'Paste a video link first.', true);
      if (mode === 'upload' && !selectedLocalFile) return statusText(exportStatus, 'Select a video file first.', true);
      const options = {
        output_format: selectedFormat, resolution: selectedResolution,
        quality: document.getElementById('qualitySelect').value
      };
      // Unknown duration means a full export; never send the invalid range 00:00:00 to 00:00:00.
      if (rangeInitialized && (mode === 'upload' || currentLoadedUrl === url)) {
        const start = Number(startSlider.value), end = Number(endSlider.value);
        if (end <= start) return statusText(exportStatus, 'Choose an end timestamp after the start.', true);
        if (start > 0 || end < totalVideoDuration) {
          options.start_time = formatSeconds(start);
          options.end_time = formatSeconds(end);
        }
      }
      setExportBusy(true);
      saveLink.classList.add('hidden');
      statusText(exportStatus, 'Starting export...');
      try {
        await window.VelaurAccount.ready;
        const account = window.VelaurAccount.profile;
        if (!account) throw new Error('Sign in with Google to export your media.');
        if (!account.access.enabled) throw new Error('Unlock your free trial from Plans or your dashboard before exporting.');
        if (mode === 'upload' && selectedLocalFile.size > account.access.limits.upload_gb * 1000000000)
          throw new Error('Your plan allows uploads up to ' + account.access.limits.upload_gb + ' GB.');
        let job;
        if (mode === 'link') {
          job = await api('/api/jobs/export', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                             body: JSON.stringify({url, ...options})});
        } else {
          const form = new FormData();
          form.append('file', selectedLocalFile);
          Object.entries(options).forEach(([key, value]) => form.append(key, value));
          job = await uploadJob(form);
        }
        await finishExport(job);
      } catch (error) {
        statusText(exportStatus, error.message, true);
        if (!(error instanceof TypeError) && !/connection|interrupted/i.test(error.message)) forgetJob();
      } finally {
        setExportBusy(false);
        document.getElementById('exportProgress').classList.add('hidden');
      }
    }

    async function toggleTheaterFullscreen() {
      try {
        const container = document.getElementById('videoContainer');
        if (document.fullscreenElement) await document.exitFullscreen();
        else if (container.requestFullscreen) await container.requestFullscreen();
        else if (videoPlayer.webkitEnterFullscreen) videoPlayer.webkitEnterFullscreen();
        else statusText(previewStatus, 'Fullscreen is not supported by this browser.', true);
      } catch (error) { statusText(previewStatus, error.message, true); }
    }

    document.addEventListener('fullscreenchange', () => {
      document.getElementById('fsIcon').innerHTML = uiIcon(document.fullscreenElement ? 'shrink' : 'expand');
    });
    document.getElementById('mediaUrl').addEventListener('input', resetPreview);
    document.getElementById('mediaUrl').addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); loadVideo(); }
    });
    window.addEventListener('beforeunload', () => { if (localObjectUrl) URL.revokeObjectURL(localObjectUrl); });
    startSlider.disabled = true;
    endSlider.disabled = true;

    (async function resumeExport() {
      let id;
      try { id = localStorage.getItem('velaurExportJobV3'); } catch { return; }
      if (!id) return;
      setExportBusy(true);
      statusText(exportStatus, 'Checking your previous export...');
      try { await finishExport(await api('/api/jobs/' + encodeURIComponent(id))); }
      catch (error) { statusText(exportStatus, error.message, true); if (!/connection|interrupted/i.test(error.message)) forgetJob(); }
      finally { setExportBusy(false); document.getElementById('exportProgress').classList.add('hidden'); }
    })();


    function uiIcon(name) {
      return '<svg class="icon' + (name === 'loader' ? ' spin' : '') +
        '" aria-hidden="true"><use href="#i-' + name + '"></use></svg>';
    }
    function updateExportSummary() {
      const quality = document.getElementById('qualitySelect').value;
      document.getElementById('exportSummary').textContent = selectedFormat === 'mp4'
        ? 'MP4 · Up to ' + selectedResolution + 'p'
        : 'MP3 · ' + ({high: '320', standard: '192', low: '128'}[quality] || '320') + ' kbps';
      for (const [id, active] of [
        ['btnFmtMp4', selectedFormat === 'mp4'], ['btnFmtMp3', selectedFormat === 'mp3'],
        ['res720', selectedResolution === '720'], ['res1080', selectedResolution === '1080'],
        ['res2160', selectedResolution === '2160']
      ]) document.getElementById(id).setAttribute('aria-pressed', String(active));
    }
    function clearMedia() {
      resetPreview();
      document.getElementById('mediaUrl').value = '';
      document.getElementById('localFileInput').value = '';
      document.getElementById('uploadBoxTitle').textContent = 'Choose a video or drag it here';
      document.getElementById('clipLengthText').textContent = 'Duration: Full';
      document.getElementById('startDisplay').textContent = '00:00:00';
      document.getElementById('endDisplay').textContent = '00:00:00';
      selectedLocalFile = null;
      if (localObjectUrl) { URL.revokeObjectURL(localObjectUrl); localObjectUrl = null; }
    }
    async function pasteVideoLink() {
      try {
        const text = await navigator.clipboard.readText();
        resetPreview();
        document.getElementById('mediaUrl').value = text.trim();
        document.getElementById('mediaUrl').focus();
      } catch {
        statusText(previewStatus, 'Click the link field and paste your video link with Ctrl+V or your device paste menu.');
        document.getElementById('mediaUrl').focus();
      }
    }
    const dropzone = document.getElementById('fileDropzone');
    for (const name of ['dragenter', 'dragover']) {
      dropzone.addEventListener(name, event => {
        event.preventDefault(); dropzone.classList.add('drag-over');
      });
    }
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', event => {
      event.preventDefault(); dropzone.classList.remove('drag-over');
      const file = event.dataTransfer.files[0];
      if (!file) return;
      if (!file.type.startsWith('video/') && !/\.(mp4|mov|mkv|webm|avi|m4v)$/i.test(file.name))
        return statusText(previewStatus, 'Choose a video file such as MP4, MOV or WebM.', true);
      handleFileSelect({target: {files: [file]}});
    });
    document.getElementById('qualitySelect').addEventListener('change', updateExportSummary);
    updateExportSummary();


    // Hover/focus help on desktop; tap toggle on touch devices; Escape dismisses.
    const faqHelp = document.getElementById('faqHelp');
    const helpWrap = faqHelp.closest('.help-wrap');
    faqHelp.addEventListener('click', () => {
      helpWrap.classList.remove('is-dismissed');
      const open = !helpWrap.classList.contains('is-open');
      helpWrap.classList.toggle('is-open', open);
      faqHelp.setAttribute('aria-expanded', String(open));
      if (!open) faqHelp.blur();
    });
    faqHelp.addEventListener('focus', () => helpWrap.classList.remove('is-dismissed'));
    helpWrap.addEventListener('pointerleave', () => helpWrap.classList.remove('is-dismissed'));
    document.addEventListener('click', event => {
      if (!helpWrap.contains(event.target)) {
        helpWrap.classList.remove('is-open');
        faqHelp.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        helpWrap.classList.add('is-dismissed');
        helpWrap.classList.remove('is-open');
        faqHelp.setAttribute('aria-expanded', 'false');
        faqHelp.blur();
      }
    });

// inline-upgrade-events-1
