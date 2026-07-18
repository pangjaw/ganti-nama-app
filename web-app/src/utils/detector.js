// =============================================================================
// detector.js — Porting logika deteksi dari core.py/app.py ke JavaScript ES6
// =============================================================================

export const BTP_JAK_LOCS = ["BOO", "CLT"];
export const BTP_BD_LOCS = ["BOP", "BTT", "COS", "MSG", "CGB", "CCR"];

const WESEL_WHITELIST = {
  "BOO": new Set(["W13", "W21A", "W21B1", "W21B2", "W23A", "W23B", "W31A", "W31B", "W31D", "W31E", "W41", "W43", "W51A1", "W51A2", "W61A1", "W61A2"]),
  "BOP": new Set(["W25", "W27A", "W27B", "W47A", "W47C", "W47D", "W67"]),
  "CLT": new Set(["W11", "W13", "W21", "W23"]),
  "MSG": new Set(["W11", "W13", "W21", "W23"])
};

const SIGNAL_PATTERN = /\b([BJLMSXU]+\.?\s?\d{1,3}[A-Z]?)\b/;

const NOISE_WORDS = new Set([
  "DISETUJUI","DISETUJUL","PISETUJUI","DIKETAHUI","DILAKSANAKAN","OLEH",
  "TANGGAL","PERIODE","PERAWATAN","NO","SC","NOMOR","ASET",
  "PENGGERAK","WESEL","ELEKTRIK","MINGGUAN","BULANAN","TAHUNAN","HERU"
]);

const TRAILING_LOC_NOISE = new Set(["AN","EEN","SIE","SIEH","SIH","SETE","S"]);

const LOC_MAP = {
  "MASENG":"MSG","CICURUG":"CCR","CILEBUT":"CLT","BOGOR":"BOO",
  "BATUTULIS":"BTT","BOGORPALEDANG":"BOP","PALEDANG":"BOP",
  "CIOMAS":"COS","CIGOMBONG":"CGB","BOJONGGEDE":"BJD","DEPOK":"BOO"
};
const LOC_CODES = new Set(["BOP","BTT","CLT","CGB","MSG","COS","BOO","CCR","BJD"]);
const SHORT_CODES = new Set(["BOO","CLT","BTT","BOP","COS","MSG","CGB","CCR","BJD"]);

// ---------- helpers ----------
function getUniqueList(items) {
  return [...new Set(items)];
}

export function getStandardLoc(text) {
  text = text.toUpperCase().replace(/\s+/g, "");
  if (text.includes("BOJONGGEDE")) return "BJD-CLT";
  if (text.includes("CIOMAS") || text.includes("COS")) return "COS";
  if (text.includes("CICURUG") || text.includes("CCR")) return "CCR";
  if (text.includes("CIGOMBONG") || text.includes("CGB")) return "CGB";
  if (text.includes("MASENG") || text.includes("MSG")) return "MSG";
  if (text.includes("BOGORPALEDANG") || text.includes("PALEDANG") || text.includes("BOP")) return "BOP";
  if (text.includes("BATUTULIS") || text.includes("BTT")) return "BTT";
  if (text.includes("CILEBUT") || text.includes("CLT")) return "CLT";
  if (text.includes("BOGOR")) return "BOO";

  // Fallback: cari keyword LOKASI / STASIUN / RESOR
  for (const keyword of ["LOKASI", "STASIUN", "RESOR"]) {
    const rx = new RegExp(`\\b${keyword}\\b`);
    const match = rx.exec(text);
    if (!match) continue;
    let tail = text.slice(match.index + match[0].length).replace(/^[\s:\-]+/, "");
    const locParts = [];
    for (const part of tail.match(/[A-Z0-9]+(?:-[A-Z0-9]+)*/g) || []) {
      if (NOISE_WORDS.has(part) || /^\d+$/.test(part)) break;
      locParts.push(part);
      if (locParts.length === 3) break;
    }
    while (locParts.length && TRAILING_LOC_NOISE.has(locParts[locParts.length - 1])) locParts.pop();
    if (locParts.length) return locParts.join(" ");
  }

  // Fallback filename: ambil setelah _ terakhir
  if (text.includes(".PDF") && text.includes("_")) {
    const tail = text.split("_").pop();
    const parts = (tail.match(/[A-Z0-9]+/g) || []).filter(p => !/^\d+$/.test(p) && p !== "PDF");
    if (parts.length) return parts.slice(0, 3).join(" ");
  }

  return "";
}

export function extractFuncloc(textCrop) {
  const lines = textCrop.split("\n");
  for (const line of lines) {
    const m = /\bLOKASI\b/.exec(line.toUpperCase());
    if (!m) continue;
    let tail = line.slice(m.index + m[0].length).trim();
    tail = tail.replace(/^[\s:]+/, "");
    const parts = tail.toUpperCase().match(/[A-Z]+(?:-[A-Z]+)*/g);
    if (!parts || !parts.length) continue;
    const first = parts[0];
    const subs = first.split("-");
    const mapped = subs.map(s => {
      s = s.trim();
      if (NOISE_WORDS.has(s)) return null;
      if (LOC_MAP[s]) return LOC_MAP[s];
      return s;
    }).filter(Boolean);
    if (mapped.length) return mapped.join("-");
  }
  return null;
}

function getPtlsLoc(textFlat, textCrop) {
  const lines = textCrop.split("\n");
  let luarIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].toUpperCase().includes("LUAR")) { luarIdx = i; break; }
  }
  if (luarIdx === -1) return getStandardLoc(textFlat);
  for (let i = luarIdx + 1; i < lines.length; i++) {
    const l = lines[i].trim().toUpperCase();
    if (!l.startsWith("LOKASI")) continue;
    const parts = l.split(/[:|]+/);
    const val = parts.length > 1 ? parts[parts.length - 1].trim() : l.slice(6).trim();
    const words = val.match(/[A-Z0-9]+(?:-[A-Z0-9]+)*/g);
    if (!words || !words.length) continue;
    const first = words[0];
    if (first.includes("-")) {
      for (const s of first.split("-")) {
        if (s === "CIGOMBONG") return "CGB";
      }
      for (const s of first.split("-")) {
        if (LOC_MAP[s]) return LOC_MAP[s];
      }
      return first;
    }
    return LOC_MAP[first] || first;
  }
  return getStandardLoc(textFlat);
}

// ---------- Dual-location scanner ----------
function getDualLoc(text) {
  const matches = [];
  for (const code of SHORT_CODES) {
    const rx = new RegExp(`\\b${code}\\b`, "g");
    let m;
    while ((m = rx.exec(text)) !== null) matches.push({ pos: m.index, code });
  }
  for (const [full, code] of Object.entries(LOC_MAP)) {
    const rx = new RegExp(`\\b${full}\\b`, "g");
    let m;
    while ((m = rx.exec(text)) !== null) matches.push({ pos: m.index, code });
  }
  if (!matches.length) return getStandardLoc(text);
  matches.sort((a, b) => a.pos - b.pos);
  const seen = new Set();
  const found = [];
  for (const { code } of matches) {
    if (!seen.has(code)) { seen.add(code); found.push(code); }
    if (found.length >= 2) break;
  }
  return found.join("-");
}

// ---------- JPL extraction ----------
function getJplInlineLoc(textSnippet) {
  const matches = [];
  for (const code of LOC_CODES) {
    const rx = new RegExp(`\\b${code}\\b`, "g");
    let m;
    while ((m = rx.exec(textSnippet)) !== null) matches.push({ pos: m.index, code });
  }
  matches.sort((a, b) => a.pos - b.pos);
  return [...new Set(matches.map(x => x.code))].join("-");
}

function extractJplAssets(textClean, textFlatRef, multiWord = false) {
  const result = [];
  const stopWords = new Set(["DISETUJUL","DIKETAHUI","OLEH","TANGGAL","ELEKTRIK","NO"]);

  // JPL Angka
  const numRx = /JPL\s+(?:ELEKTRIK\s+)?(?:NO[.\s]*)?([0-9]+[A-Z]*)/g;
  let m;
  while ((m = numRx.exec(textClean)) !== null) {
    const aid = `JPL ${m[1].trim()}`;
    const snippet = textClean.slice(m.index + m[0].length, m.index + m[0].length + 25);
    let loc = getJplInlineLoc(snippet);
    if (!loc) loc = getStandardLoc(textClean.slice(m.index + m[0].length));
    if (loc === "LOKASI") loc = getStandardLoc(textFlatRef);
    if (!result.some(a => a.id === aid)) result.push({ id: aid, loc });
  }

  // JPL Huruf
  const wordRx = multiWord
    ? /JPL\s+([A-Z]+(?:\s+[A-Z\-]+)*)/g
    : /\bJPL\s+([A-Z]+)\b/g;
  while ((m = wordRx.exec(textClean)) !== null) {
    let aid = `JPL ${m[1].trim()}`;
    aid = aid.split(/\s+\b(?:LOKASI|DISETUJUI|DISETUJUL|PISETUJUI|DIKETAHUI|TANGGAL|OLEH)\b/)[0].trim();
    const wordParts = aid.replace("JPL ", "").split(/\s+/);
    if (wordParts.every(p => stopWords.has(p.replace(/[.,;-]/g, "")))) continue;
    const snippet = textClean.slice(m.index + m[0].length, m.index + m[0].length + 25);
    let loc = getJplInlineLoc(snippet);
    if (!loc) loc = getStandardLoc(textClean.slice(m.index + m[0].length));
    if (loc === "LOKASI") loc = getStandardLoc(textFlatRef);
    if (/[A-Z]{3}\s*-\s*[A-Z]{3}/.test(aid)) loc = "";
    if (!result.some(a => a.id === aid)) result.push({ id: aid, loc });
  }

  if (!result.length) result.push({ id: "JPL", loc: getStandardLoc(textFlatRef) });
  return result;
}

// ---------- Wesel extraction ----------
function extractWeselIds(text, allowGeneric = false) {
  const result = [];
  const patterns = [
    /PENGGERAK\s+WESEL(?:\s+ELEKTRIK)?\s+(?:W\s*\.?\s*)?(\d{1,3})\s*([A-Z]?\d?)\b/g,
    /(?<![\\/|!])\bW(?!SL)\s*\.?\s*(\d{1,3})\s*([A-Z]?\d?)\b/g,
  ];
  if (allowGeneric) patterns.push(/(?<![\\/|!])\b(?:W\s*\.?\s*)?(\d{1,3})\s*([A-Z]\d?)\b/g);
  for (const rx of patterns) {
    let m;
    while ((m = rx.exec(text)) !== null) {
      result.push(`W${m[1]}${m[2]}`.replace(/\s/g, ""));
    }
  }
  return getUniqueList(result);
}

// ---------- Radio Waystation ----------
function extractRadioWaystationAssets(text) {
  const result = [];
  const stopWords = new Set(["LOKASI","DISETUJUI","DISETUJUL","PISETUJUI","DIKETAHUI","TANGGAL","PERIODE","PERAWATAN","DILAKSANAKAN","OLEH","NO","SC"]);
  const locCodes = new Set([...BTP_JAK_LOCS, ...BTP_BD_LOCS]);
  const longNames = new Set(["BOGOR","CILEBUT","BATUTULIS","BOGORPALEDANG","PALEDANG","CIOMAS","MASENG","CIGOMBONG"]);

  const rx = /\bTLK\d+\s*:\s*(WS\b[^:]+)/g;
  let m;
  while ((m = rx.exec(text)) !== null) {
    const tokens = m[1].match(/[A-Z0-9]+/g) || [];
    const aidParts = [];
    let loc = "";
    for (const token of tokens) {
      if (stopWords.has(token)) break;
      if (locCodes.has(token) || longNames.has(token)) {
        loc = getStandardLoc(token);
        break;
      }
      aidParts.push(token);
    }
    if (aidParts.length && aidParts[0] === "WS") {
      if (!loc) loc = getStandardLoc(text.slice(m.index + m[0].length));
      if (loc === "LOKASI") loc = getStandardLoc(text);
      const aid = aidParts.join(" ");
      if (!result.some(a => a.id === aid && a.loc === loc)) result.push({ id: aid, loc });
    }
  }
  if (!result.length) result.push({ id: "WS", loc: getStandardLoc(text) });
  return result;
}

// ======================= MAIN DETECT API =======================

export function detectDoc(textFlat, textCrop, filenameUpper) {
  let kode = "";
  let kategori = "";
  let assets = [];

  // ---------- OCR-based detection ----------

  // POINT LOCK
  if (textFlat.includes("POINT LOCK") || textFlat.includes("PENGAMAN WESEL")) {
    kode = "BPBYE12"; kategori = "POINT LOCK";
    const wMatch = extractWeselIds(textFlat, true);
    if (wMatch.length) {
      for (const w of wMatch) {
        let wLoc = null;
        for (const line of textCrop.split("\n")) {
          if (line.includes(w) && !line.toUpperCase().includes("PERAWATAN")) {
            wLoc = getDualLoc(line); break;
          }
        }
        const loc = wLoc || extractFuncloc(textCrop) || getStandardLoc(textFlat);
        if (loc === "BOO" && w !== "W81") continue;
        assets.push({ id: w, loc });
      }
    } else {
      const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
      assets.push({ id: "PL", loc });
    }
  }

  // WESEL
  else if (textFlat.includes("PERAWATAN WESEL") || textFlat.includes("PENGGERAK WESEL")) {
    kode = "BPBYE1"; kategori = "WESEL";
    const wMatch = extractWeselIds(textFlat, true);
    if (wMatch.length) {
      for (const w of wMatch) {
        let wLoc = null;
        for (const line of textCrop.split("\n")) {
          if (line.includes(w) && !line.toUpperCase().includes("PERAWATAN")) {
            wLoc = getDualLoc(line); break;
          }
        }
        const loc = wLoc || extractFuncloc(textCrop) || getStandardLoc(textFlat);
        const allowed = WESEL_WHITELIST[loc];
        if (allowed && !allowed.has(w)) continue;
        assets.push({ id: w, loc });
      }
    } else {
      const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
      assets.push({ id: "W_UNKNOWN", loc });
    }
  }

  // PDSE
  else if (textFlat.includes("PERALATAN DALAM PERSINYALAN ELEKTRIK")) {
    kode = "BPBYE2"; kategori = "PDSE";
    const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
    assets.push({ id: "", loc });
  }

  // PTPP
  else if (textFlat.includes("TELEKOMUNIKASI DI PINTU PERLINTASAN")) {
    kode = "BPBKS17"; kategori = "PTPP";
    let textClean = textFlat.replace(/\bJPL\d+\b/g, "");
    for (const marker of ["NO ITEM", "ITEM PERAWATAN"]) {
      const idx = textClean.toUpperCase().indexOf(marker);
      if (idx >= 0) { textClean = textClean.slice(0, idx); break; }
    }
    assets = extractJplAssets(textClean, textFlat, false);
    // Dedup
    const dedup = {};
    for (const a of assets) {
      if (!dedup[a.id]) dedup[a.id] = { ...a };
      else {
        const existingLocs = dedup[a.id].loc.split("-");
        const newLocs = a.loc.split("-");
        const merged = [...new Set([...existingLocs, ...newLocs])];
        dedup[a.id].loc = merged.join("-");
      }
    }
    assets = Object.values(dedup);
    // Prefer JPL from filename
    // Prefer JPL from filename — tapi skip noise word seperti ELEKTRIK
    const fnMatch = filenameUpper.match(/JPL\s+(?:ELEKTRIK\s+)?([A-Z0-9]+)/);
    if (fnMatch) {
      const fnJpl = `JPL ${fnMatch[1]}`;
      const fnLoc = getStandardLoc(filenameUpper);
      const ocrMatch = assets.find(a => a.id === fnJpl);
      assets = ocrMatch ? [ocrMatch] : [{ id: fnJpl, loc: fnLoc || "" }];
    } else if (assets.length) {
      assets = [assets[0]];
    }
  }

  // PINTU PERLINTASAN (tanpa TELEKOMUNIKASI)
  else if (textFlat.includes("PINTU PERLINTASAN") && !textFlat.includes("TELEKOMUNIKASI")) {
    kode = "BPBKS17"; kategori = "PINTU PERLINTASAN";
    let textClean = textFlat.replace(/\bJPL\d+\b/g, "");
    assets = extractJplAssets(textClean, textFlat, true);
    if (!assets.length) {
      const fnMatch = filenameUpper.match(/JPL\s+([A-Z0-9]+)/);
      if (fnMatch) {
        assets = [{ id: `JPL ${fnMatch[1]}`, loc: getStandardLoc(filenameUpper) || "" }];
      } else {
        const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
        assets = [{ id: "", loc }];
      }
    }
  }

  // PTDS
  else if (textFlat.includes("TELEKOMUNIKASI DI STASIUN")) {
    kode = "BPBKS15"; kategori = "PTDS";
    const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
    assets.push({ id: "", loc });
  }

  // PTLS
  else if (textFlat.includes("TELEKOMUNIKASI DI LUAR STASIUN")) {
    kode = "BPBKS16"; kategori = "PTLS";
    const loc = getPtlsLoc(textFlat, textCrop);
    assets.push({ id: "", loc });
  }

  // RADIO BASESTATION
  else if (textFlat.includes("RADIO BASESTATION")) {
    const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
    if (textFlat.includes("TAIT")) { kode = "BPBKF3"; kategori = "RADIO BASESTATION TAIT"; }
    else if (textFlat.includes("DIGITAL")) { kode = "BPBKF2"; kategori = "RADIO BASESTATION DIGITAL"; }
    else { kode = "BPBKF1"; kategori = "RADIO BASESTATION"; }
    assets.push({ id: "", loc });
  }

  // WAYSTATION / RADIO WAYSTATION
  else if (textFlat.includes("SISTEM WAYSTATION") || textFlat.includes("RADIO WAYSTATION") || textFlat.includes("RADIO WAY STATION")) {
    if (textFlat.includes("SISTEM WAYSTATION")) {
      kode = "BPBKS5"; kategori = "SISTEM WAYSTATION";
      const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
      assets.push({ id: "", loc });
    } else {
      kode = "BPBKS16"; kategori = "RADIO WAYSTATION";
      assets = extractRadioWaystationAssets(textFlat);
    }
  }

  // CTC-CTS
  else if (textFlat.includes("CTC") && textFlat.includes("CTS")) {
    kode = "BPBYE4"; kategori = "CTC-CTS";
    const loc = extractFuncloc(textCrop) || getStandardLoc(textFlat);
    assets.push({ id: "", loc });
  }

  // AXLE COUNTER
  else if (textFlat.includes("PERAWATAN AXLE COUNTER")) {
    kode = "BPBYE7"; kategori = "AXLE COUNTER";
    const zpRx = /\bZP\s?(\d{1,3})([A-Z]{1,2})?\b(?!\.\d)/g;
    let m;
    const zpMatches = [];
    while ((m = zpRx.exec(textFlat)) !== null) {
      if (m[1] === "43" && !m[2]) continue;
      zpMatches.push({ id: `ZP ${m[1]}${m[2] || ""}`, pos: m.index });
    }
    if (zpMatches.length) {
      const seen = new Set();
      for (const { id: zId, pos } of zpMatches) {
        if (seen.has(zId)) continue;
        seen.add(zId);
        let zpLoc = null;
        for (const line of textCrop.split("\n")) {
          if (line.includes(zId) && !line.toUpperCase().includes("PERAWATAN")) {
            zpLoc = getDualLoc(line); break;
          }
        }
        const loc = zpLoc || extractFuncloc(textCrop) || getDualLoc(textFlat);
        assets.push({ id: zId, loc });
      }
    } else {
      const loc = extractFuncloc(textCrop) || getDualLoc(textFlat);
      assets.push({ id: "ZP", loc });
    }
  }

  // PERAGA SINYAL / PERAWATAN SINYAL
  else if (textFlat.includes("PERAGA SINYAL") || textFlat.includes("PERAWATAN SINYAL")) {
    kode = "BPBYE3"; kategori = "PERAGA SINYAL";
    const signalMatches = textFlat.match(SIGNAL_PATTERN) || [];
    const validSignals = [];
    for (const s of signalMatches) {
      const sClean = s.replace(/\s/g, "").replace(/\./g, "");
      if (/^M\d+$/.test(sClean)) continue;
      if (/^[BJLMSXU]+\d+/.test(sClean)) validSignals.push(sClean);
    }
    if (validSignals.length) {
      const uniqueSig = getUniqueList(validSignals);
      for (const s of uniqueSig) {
        let sigLoc = null;
        for (const line of textCrop.split("\n")) {
          const lineFlat = line.replace(/\./g, "").replace(/\s/g, "");
          if ((line.includes(s) || lineFlat.includes(s)) && !line.toUpperCase().includes("PERAWATAN")) {
            sigLoc = getDualLoc(line); break;
          }
        }
        const loc = sigLoc || getDualLoc(textFlat);
        assets.push({ id: s, loc });
      }
    } else {
      const loc = getDualLoc(textFlat);
      assets.push({ id: "", loc });
    }
  }

  // CATU DAYA
  else if (textFlat.includes("CATU DAYA")) {
    const cdaLines = textCrop.split("\n").filter(l => l.toUpperCase().includes("CDA"));
    const combinedCda = cdaLines.join(" ").toUpperCase();
    if (combinedCda.includes("ER RADIO")) { kode = "BPBYE14"; kategori = "CATU DAYA ER RADIO"; }
    else if (combinedCda.includes("ER SINYAL")) { kode = "BPBYE14"; kategori = "CATU DAYA ER SINYAL"; }
    else { kode = "BPBYE14"; kategori = "CATU DAYA"; }
    const loc = extractFuncloc(textCrop) || getDualLoc(textFlat);
    assets.push({ id: "", loc });
  }

  // SERAT OPTIK ER
  else if ((textFlat.includes("SERAT OPTIK") && /\bER\b/.test(textFlat)) ||
           (!textFlat.trim() && filenameUpper.includes("SERAT OPTIK") && filenameUpper.includes(" ER "))) {
    kode = "BPBKF4"; kategori = "SERAT OPTIK";

    // === 1. Deteksi sub-type ER: SINYAL > RADIO > TELKOM > generic ER ===
    let erType = null;
    // OCR priority
    if (/\bER\s+SINYAL\b/.test(textFlat)) {
      erType = "ER SINYAL";
    } else if (/\bER\s+RADIO\b/.test(textFlat)) {
      erType = "ER RADIO";
    } else if (textFlat.includes("TELKOM")) {
      erType = "ER TELKOM";
    }
    // Filename fallback (terpisah per keyword)
    if (!erType) {
      if (filenameUpper.includes("SINYAL")) {
        erType = "ER SINYAL";
      } else if (filenameUpper.includes("RADIO")) {
        erType = "ER RADIO";
      } else if (filenameUpper.includes("TELKOM")) {
        erType = "ER TELKOM";
      }
    }
    if (!erType) erType = "ER";

    // === 2. Scan OTB numbers ===
    let firstOtb = 0, otbMin = 1, otbMax = 1;
    let hasOtbNumbers = false;

    // Filter OTB: exclude ODF/OTB (core count) via check on preceding char
    const allOtbNums = [];
    const simpleOtbRx = /\bOTB\s+(\d+)\b/g;
    let om;
    while ((om = simpleOtbRx.exec(textFlat)) !== null) {
      const preChar = textFlat[om.index - 1] || "";
      if (preChar === "/" || /[A-Za-z]/.test(preChar)) continue;
      allOtbNums.push(+om[1]);
    }
    if (allOtbNums.length) {
      otbMin = Math.min(...allOtbNums);
      otbMax = Math.max(...allOtbNums);
      firstOtb = otbMin;
      hasOtbNumbers = true;
    } else {
      // Fallback from filename
      const rangeMatch = filenameUpper.match(/OTB\s+(\d+)-(\d+)/);
      const singleMatch = filenameUpper.match(/OTB\s+(\d+)(?!\s*-)/);
      if (rangeMatch) {
        otbMin = +rangeMatch[1]; otbMax = +rangeMatch[2]; firstOtb = otbMin;
        hasOtbNumbers = true;
      } else if (singleMatch) {
        otbMin = +singleMatch[1]; otbMax = otbMin; firstOtb = otbMin;
        hasOtbNumbers = true;
      }
    }

    // === 3. Ekstrak lokasi dari OCR ===
    let loc = null;
    for (const line of textCrop.split("\n")) {
      const ul = line.toUpperCase();
      if (ul.includes("OTB") && ul.includes("ER")) {
        const parts = ul.split(":");
        if (parts.length >= 2) {
          let after = parts[parts.length - 1].trim();
          after = after.replace(/OTB\s+FO\s+\d+\s*/g, "");
          after = after.replace(/OTB\s+FO\s+/g, "");            // OTB FO tanpa digit
          after = after.replace(/OTB\s+\d+\s*/g, "");
          after = after.replace(/TRA\d+\s*:\s*/g, "");
          after = after.replace(/^ER\s+SINYAL\s+/, "");
          after = after.replace(/^ER\s+RADIO\s+/, "");
          after = after.replace(/^ER\s+TELKOM\s+/, "");
          after = after.replace(/^ER\s+/, "");
          loc = after.trim();
          if (loc) break;
        }
      }
    }
    if (!loc) {
      loc = getStandardLoc(filenameUpper) || extractFuncloc(textCrop) || getStandardLoc(textFlat);
    }

    assets = [{ id: erType, loc, firstOtb, erType, otbMin, otbMax, hasOtbNumbers }];
  }

  // SERAT OPTIK non-ER (JPL / Bulanan)
  else if (textFlat.includes("SERAT OPTIK")) {
    kode = "BPBKF4"; kategori = "SERAT OPTIK";
    const fnLoc = getStandardLoc(filenameUpper);
    let loc = fnLoc || extractFuncloc(textCrop) || getStandardLoc(textFlat);

    // Scan OCR for TRA lines with JPL
    const jplSet = new Set();
    for (const ocrLine of textCrop.split("\n")) {
      const ul = ocrLine.toUpperCase().trim();
      const m = ul.match(/TRA\d+\s*:\s*OTB\s+FO\s+JPL\s+(\S+)/);
      if (m) {
        let jplId = m[1];
        jplId = jplId.replace(/\s+[A-Z][A-Z].*/, "");
        jplSet.add(jplId);
      }
    }

    if (jplSet.size) {
      assets = [...jplSet].sort().map(jplId => ({ id: `JPL ${jplId}`, loc }));
    } else {
      const fnMatch = filenameUpper.match(/JPL\s+(\d+[A-Z]*)/);
      if (fnMatch) {
        assets = [{ id: `JPL ${fnMatch[1]}`, loc: loc || "" }];
      } else {
        const seqMatch = filenameUpper.match(/_0*(\d+)\s/);
        const seqNum = seqMatch ? +seqMatch[1] : 1;
        assets = [{ id: "", loc, seqNum, isBulanan: true }];
      }
    }
  }

  // ---------- Filename-based fallback ----------
  if (!assets.length) {
    const loc = getStandardLoc(filenameUpper);

    if (filenameUpper.includes("WESEL")) {
      kode = "BPBYE1"; kategori = "WESEL";
      // Safety: jangan ambil ID dari filename (bisa salah seperti W222/W322R)
      assets = [{ id: "W_UNKNOWN", loc }];
    } else if (filenameUpper.includes("POINT LOCK")) {
      kode = "BPBYE12"; kategori = "POINT LOCK";
      assets = [{ id: "PL", loc }];
    } else if (filenameUpper.includes("AXLE COUNTER")) {
      kode = "BPBYE7"; kategori = "AXLE COUNTER";
      // Safety: jangan ambil ID dari filename (bisa salah seperti ZP 2)
      assets = [{ id: "ZP", loc }];
    } else if (filenameUpper.includes("SINYAL")) {
      kode = "BPBYE3"; kategori = "PERAGA SINYAL";
      assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("SERAT OPTIK")) {
      kode = "BPBKF4"; kategori = "SERAT OPTIK";
      if (filenameUpper.includes("ER TELKOM")) assets = [{ id: "ER TELKOM", loc }];
      else if (filenameUpper.includes(" ER ") || filenameUpper.endsWith(" ER")) assets = [{ id: "ER", loc }];
      else assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("CTC") && filenameUpper.includes("CTS")) {
      kode = "BPBYE4"; kategori = "CTC-CTS"; assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("RADIO BASESTATION")) {
      if (filenameUpper.includes("TAIT")) { kode = "BPBKF3"; kategori = "RADIO BASESTATION TAIT"; }
      else if (filenameUpper.includes("DIGITAL")) { kode = "BPBKF2"; kategori = "RADIO BASESTATION DIGITAL"; }
      else { kode = "BPBKF1"; kategori = "RADIO BASESTATION"; }
      assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("SISTEM WAYSTATION")) {
      kode = "BPBKS5"; kategori = "SISTEM WAYSTATION"; assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("RADIO WAYSTATION") || filenameUpper.includes("RADIO WAY STATION")) {
      kode = "BPBKS16"; kategori = "RADIO WAYSTATION"; assets = [{ id: "WS", loc }];
    } else if (filenameUpper.includes("PTPP") || filenameUpper.includes("PINTU PERLINTASAN")) {
      kode = "BPBKS17"; kategori = "PTPP";
      const fnMatch = filenameUpper.match(/JPL\s+(?:ELEKTRIK\s+)?([A-Z0-9]+)/);
      assets = fnMatch ? [{ id: `JPL ${fnMatch[1]}`, loc: loc || "" }] : [{ id: "", loc: loc || "" }];
    } else if (filenameUpper.includes("PDSE") || filenameUpper.includes("PERALATAN DALAM PERSINYALAN")) {
      kode = "BPBYE2"; kategori = "PDSE"; assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("PTDS") || filenameUpper.includes("TELEKOMUNIKASI DI STASIUN")) {
      kode = "BPBKS15"; kategori = "PTDS"; assets = [{ id: "", loc }];
    } else if (filenameUpper.includes("PTLS") || filenameUpper.includes("TELEKOMUNIKASI DI LUAR STASIUN")) {
      kode = "BPBKS16"; kategori = "PTLS"; assets = [{ id: "", loc }];
    }
  }

  return { kode, kategori, assets };
}

export function getBtp(loc) {
  return BTP_JAK_LOCS.includes(loc) ? "BTP JAK" : "BTP BD";
}

export function buildFilename(prefixPeriode, kode, jenis, identitas, tglFull, formatBd) {
  identitas = identitas.replace(/PERAGA SINYAL/g, "SINYAL").replace(/PERAWATAN SINYAL/g, "SINYAL");
  if (formatBd) {
    return `${prefixPeriode}_Resor 1.21 Boo_${kode}_${jenis}_${identitas}_${tglFull}.pdf`;
  }
  return `${jenis.toUpperCase()} ${identitas} ${tglFull}.pdf`;
}
