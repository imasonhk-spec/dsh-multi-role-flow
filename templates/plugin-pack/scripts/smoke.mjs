#!/usr/bin/env node
/**
 * 能力包 smoke：零依赖、只读，跑完给 PASS/FAIL 计数。
 * 用法（在 pack 目录）：node scripts/smoke.mjs
 * 覆盖：package.json 契约、patch 文件、浏览器模块 id、health / 404 / ping 行为。
 * 不装依赖、不写项目文件；任何一条失败即退出码 1。
 */
import { readFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { Readable } from 'node:stream';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');

let pass = 0;
const failures = [];

function check(name, cond, detail = '') {
  if (cond) {
    pass += 1;
    console.log(`PASS ${name}`);
  } else {
    failures.push(`${name}${detail ? `：${detail}` : ''}`);
    console.log(`FAIL ${name}${detail ? `：${detail}` : ''}`);
  }
}

function parseJson(rel) {
  return JSON.parse(readFileSync(resolve(ROOT, rel), 'utf8'));
}

function mockRes() {
  const headers = {};
  return {
    status: 0,
    body: '',
    headers,
    setHeader(k, v) {
      headers[String(k).toLowerCase()] = v;
    },
    writeHead(status) {
      this.status = status;
    },
    end(body) {
      this.body = String(body || '');
    },
  };
}

function mockGetReq(path) {
  return { url: path, method: 'GET', on() {} };
}

function mockPostReq(path, obj) {
  const stream = Readable.from([Buffer.from(JSON.stringify(obj), 'utf8')]);
  stream.url = path;
  stream.method = 'POST';
  return stream;
}

async function main() {
  const pkg = parseJson('package.json');
  const id = pkg?.dsh?.capabilityPack?.id;
  const cap = pkg?.dsh?.capabilityPack || {};

  check('package.json 可解析且 name 非空', typeof pkg.name === 'string' && pkg.name.length > 0);
  check('version 是 x.y.z', /^\d+\.\d+\.\d+/.test(String(pkg.version || '')));
  check('type=module 且 main=./index.js', pkg.type === 'module' && pkg.main === './index.js');
  check('dsh.bundle.patch 存在', typeof pkg?.dsh?.bundle?.patch === 'string');
  check('capabilityPack.id 非空', typeof id === 'string' && id.length > 0);
  for (const key of ['title', 'description', 'entryKey', 'order', 'category', 'version', 'tags', 'icon']) {
    check(`capabilityPack.${key} 存在`, cap[key] !== undefined && cap[key] !== '');
  }
  check('entryKey == cap:<id>', cap.entryKey === `cap:${id}`);
  check('capabilityPack.version 与 package version 一致', String(cap.version || '').replace(/^v/, '') === String(pkg.version));
  check('openEvent == cappacks:open-<id>', cap.openEvent === `cappacks:open-${id}`);

  const patchRel = String(pkg?.dsh?.bundle?.patch || '').replace(/^\.\//, '');
  check('patch 文件真实存在', patchRel && existsSync(resolve(ROOT, patchRel)), patchRel);
  if (patchRel && existsSync(resolve(ROOT, patchRel))) {
    const patch = readFileSync(resolve(ROOT, patchRel), 'utf8');
    check('patch 含本包 id', patch.includes(`id: ${id}`));
    check('patch 含本包包名', patch.includes(pkg.name));
  }

  for (const rel of ['index.js', 'client.js', 'icon.svg']) {
    check(`${rel} 存在`, existsSync(resolve(ROOT, rel)));
  }

  // 浏览器模块 id 必须等于 manifest 包名（写成短 id = 打开没反应）
  if (existsSync(resolve(ROOT, 'client.js'))) {
    const client = readFileSync(resolve(ROOT, 'client.js'), 'utf8');
    const idMatch = /__ModuleLoader__\.load\(\s*\{\s*id:\s*['"]([^'"]+)['"]/.exec(client);
    check('client.js 用 __ModuleLoader__.load', Boolean(idMatch));
    check('浏览器模块 id == manifest 包名', Boolean(idMatch) && idMatch[1] === pkg.name, idMatch ? idMatch[1] : '未匹配');
  }

  // 宿主半行为
  const mod = await import(pathToFileURL(resolve(ROOT, 'index.js')).href);
  check('index.js 导出 VERSION 且与 package.json 一致', mod.VERSION === pkg.version, `VERSION=${mod.VERSION}`);
  check('index.js 导出 API_PREFIX == /api/<id>', mod.API_PREFIX === `/api/${id}`);
  check('index.js 导出 apply 与 inject', typeof mod.apply === 'function');
  check('MANIFEST.id == capabilityPack.id', mod.MANIFEST?.id === id);

  const res1 = mockRes();
  await mod.handleRequest(mockGetReq(`${mod.API_PREFIX}/health`), res1);
  let health = null;
  try {
    health = JSON.parse(res1.body);
  } catch {
    /* 下面判 */
  }
  check('GET /health 200', res1.status === 200);
  check('health 含 ok/id/version/entryKey/routes',
    Boolean(health && health.ok === true && health.id === id && health.version && health.entryKey && Array.isArray(health.routes)));

  const res2 = mockRes();
  await mod.handleRequest(mockGetReq(`${mod.API_PREFIX}/nope`), res2);
  let nf = null;
  try {
    nf = JSON.parse(res2.body);
  } catch {
    /* 下面判 */
  }
  check('未知路由 404 + 结构化 hint', res2.status === 404 && Boolean(nf && nf.error === 'NOT_FOUND' && nf.hint && nf.method && nf.path));

  const res3 = mockRes();
  await mod.handleRequest(mockPostReq(`${mod.API_PREFIX}/ping`, { text: 'hello' }), res3);
  let ping = null;
  try {
    ping = JSON.parse(res3.body);
  } catch {
    /* 下面判 */
  }
  check('POST /ping 回显 echo', res3.status === 200 && Boolean(ping && ping.ok === true && ping.echo === 'hello'));

  const res4 = mockRes();
  await mod.handleRequest(mockGetReq('/api/other-prefix/x'), res4);
  check('前缀外请求 404', res4.status === 404);

  console.log(`\n${pass} passed, ${failures.length} failed`);
  if (failures.length) {
    for (const f of failures) console.log(`  - ${f}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('smoke 崩溃：', err);
  process.exit(2);
});
