// =============================================================================
// fsHandler.js — File System Access API + JSZip fallback + HTTP API (desktop)
// Desktop (pywebview): POST /api/select-folder + /api/save-file
// Browser: File System Access API + ZIP download
// =============================================================================

import JSZip from 'jszip';

const API = '/api';

async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`${API}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Ask user to pick a directory for saving renamed files.
 * Desktop: POST /api/select-folder. Browser: File System Access API.
 * @returns {Promise<{name:string, isDesktop: boolean}|null>}
 */
export async function pickDirectory() {
  // Try desktop API first
  const data = await apiPost('select-folder');
  if (data && data.path) {
    return { name: data.name, isDesktop: true, path: data.path };
  }

  // Browser: File System Access API
  if (!window.showDirectoryPicker) {
    return null; // will use ZIP
  }
  try {
    const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
    return { name: handle.name, isDesktop: false, handle };
  } catch (err) {
    if (err.name === 'AbortError') return null;
    return null;
  }
}

/**
 * Write a file to selected directory.
 * Desktop: POST /api/save-file. Browser: FileSystemDirectoryHandle.
 * @param {{name:string, isDesktop:boolean, handle?:FileSystemDirectoryHandle, path?:string}} dir
 * @param {string} filename
 * @param {ArrayBuffer|Uint8Array} data
 */
export async function writeFileToDir(dir, filename, data) {
  if (dir.isDesktop) {
    // Desktop: send base64 via API
    const bytes = new Uint8Array(data);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const result = await apiPost('save-file', { filename, data: btoa(binary) });
    if (!result || !result.ok) throw new Error('Gagal menyimpan file');
    return;
  }

  // Browser: File System Access API
  if (!dir.handle) throw new Error('No directory handle');
  const fileHandle = await dir.handle.getFileHandle(filename, { create: true });
  const writable = await fileHandle.createWritable({ keepExistingData: false });
  await writable.write(data);
  await writable.close();
}

/**
 * Save all processed files as ZIP (fallback when no folder selected).
 * @param {Array<{name: string, data: ArrayBuffer}>} files
 * @returns {Promise<Blob>}
 */
export async function createZipBlob(files) {
  const zip = new JSZip();
  for (const f of files) {
    zip.file(f.name, f.data);
  }
  return await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
}

/**
 * Trigger browser download of a blob as a file.
 * @param {Blob} blob
 * @param {string} filename
 */
export function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
