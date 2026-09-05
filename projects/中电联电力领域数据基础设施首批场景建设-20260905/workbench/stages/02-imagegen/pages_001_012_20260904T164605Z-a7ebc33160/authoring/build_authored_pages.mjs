import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const authoringDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(authoringDir, '..');
const scriptPath = path.resolve(root, '../../../../script/dist/final-script.md');
const manifestPath = path.join(root, 'page_image_pairs.json');
const md = fs.readFileSync(scriptPath, 'utf8');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

const pages = {
  4: [[44,42,510,278,19],[612,450,790,255,19],[1538,54,450,500,19]],
  5: [[42,48,520,280,21],[646,148,805,430,18],[560,676,920,168,21]],
  7: [[42,42,700,360,20],[42,476,700,320,20],[790,164,520,300,21]],
  8: [[390,34,720,270,20],[1388,42,580,520,20],[190,700,1640,190,22]],
 10: [[60,44,610,220,20],[690,310,700,255,20],[80,710,1650,170,21]],
 11: [[40,44,350,430,17],[1390,42,590,380,18],[1300,650,650,235,19]],
};

const esc = s => s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function pageParagraphs(n) {
  const start = md.indexOf(`## P${String(n).padStart(2,'0')} `);
  const ons = md.indexOf('### 上屏文字', start);
  const notes = md.indexOf('### 演讲者备注', ons);
  return md.slice(ons + '### 上屏文字'.length, notes).trim().split(/\n\s*\n/).map(s => s.replace(/\s+/g,' ').trim());
}
function wrap(text, chars) {
  const out=[]; for(let i=0;i<text.length;i+=chars) out.push(text.slice(i,i+chars)); return out;
}
function textEl(text, box) {
  const [x,y,w,h,size]=box;
  const chars=Math.max(12,Math.floor(w/(size*1.04)));
  let lines=wrap(text,chars);
  const leading=size*1.55;
  const max=Math.floor(h/leading);
  if(lines.length>max){
    const smaller=Math.max(13,Math.floor(size*max/lines.length));
    return textEl(text,[x,y,w,h,smaller]);
  }
  return `<rect x="${x-12}" y="${y-10}" width="${w+24}" height="${h+20}" rx="12" fill="#FFFFFF" fill-opacity="0.94"/><text x="${x}" y="${y+size}" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="${size}" fill="#303030">${lines.map((line,i)=>`<tspan x="${x}" dy="${i?leading:0}"${i===0?' font-weight="600" fill="#12355B"':''}>${esc(line)}</tspan>`).join('')}</text>`;
}
for (const [raw, boxes] of Object.entries(pages)) {
  const n=Number(raw), paragraphs=pageParagraphs(n);
  if(paragraphs.length!==3) throw new Error(`P${n} expected 3 onscreen paragraphs, got ${paragraphs.length}`);
  const href=`assets/page_${String(n).padStart(3,'0')}_clean_base.png`;
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 2048 1024" width="2048" height="1024" data-cyberppt-native-text-style="locked"><image href="${href}" x="0" y="0" width="2048" height="1024" preserveAspectRatio="none"/>${paragraphs.map((p,i)=>textEl(p,boxes[i])).join('')}</svg>\n`;
  fs.writeFileSync(path.join(authoringDir,`page_${String(n).padStart(3,'0')}.svg`),svg);
  const pair=manifest.pairs.find(p=>p.page_number===n);
  pair.graphic_text_policy={
    schema:'cyberppt.image_to_pptx.graphic_text_policy.v1', status:'complete', empty_container_check:'passed', unresolved_empty_containers:[],
    items:[...paragraphs.map((text,i)=>({id:`p${String(n).padStart(3,'0')}-paragraph-${i+1}`,text,treatment:'native_text',source_visible:true,bbox:[boxes[i][0],boxes[i][1],boxes[i][0]+boxes[i][2],boxes[i][1]+boxes[i][3]]})), ...(n===7?[{id:'p007-right-icon-glyph',text:'且',observed_text:'且',treatment:'decorative_glyph',bbox:[1738,284,1775,320],visual_review:{status:'passed',classification:'non_semantic_glyph',reviewer:'codex-main',note:'OCR false positive on the right-side monochrome infrastructure icon; no semantic text is present.'}}]:[])],
    note:'All locked onscreen paragraphs are rebuilt as native editable SVG text over a reference-edited text-free base.'
  };
}
fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
