// Teste do painel num navegador de verdade (Chromium sem janela), sem o carrinho: usa a demonstração e uma porta serial falsa que se comporta
// como o robo.ino. Precisa do Playwright:  npm i playwright && npx playwright install chromium   e depois:  node maker/painel/testar_painel.js
const { chromium } = require('playwright');
const path = require('path');
const url = 'file://' + path.join(__dirname, 'index.html');

// porta serial falsa: reinicia ao abrir, responde aos comandos e manda telemetria (a mesma linguagem do robo.ino)
const portaFalsa = () => {
  window.__enviados = [];
  const enc = new TextEncoder(), dec = new TextDecoder();
  let ctl, modo = 0, passos = 1200, ms = 5000, timer = null;
  const cfg = { eps_inicial: 0.3, eps_minimo: 0.05, eps_tau: 1200, ciclos_por_acao: 3, margem_min: 14, adaptar_margem: 1, palpite: 1, meta_passos: 0, meta_minutos: 0 };
  const tx = (t) => ctl.enqueue(enc.encode(t + '\n'));
  const tele = () => { ms += 150; if (modo === 2 && Math.random() < 0.3) passos++; tx(`~${ms},${(40 + 30 * Math.sin(ms / 2000)).toFixed(1)},55,0,${modo},${modo === 2 ? 0 : -1},0,16,${passos},0.130`); };
  const comando = (l) => {
    l = l.trim(); window.__enviados.push(l);
    if (l === 'painel 1') { clearInterval(timer); timer = setInterval(tele, 150); tx('painel: telemetria ligada'); }
    else if (l === 'cfg?') { Object.entries(cfg).forEach(([k, v]) => tx(`CFG ${k}=${v}`)); tx(`ESTADO modo=${modo} passos=${passos} eps=0.130 margem=16 margem_lento=20 painel=1`); }
    else if (l.startsWith('cfg ')) { const [, k, v] = l.split(' '); cfg[k] = Number(v); tx(`CFG ${k}=${v}`); }
    else if (l === 'e') { tx('bloco,passos_de_treino,nota_media,quase_batidas,freios,distancia_do_freio_cm  (cada bloco = 100 passos)'); for (let i = 1; i <= 12; i++) tx(`${i},${i * 100},${(-0.8 + i * 0.07).toFixed(3)},${Math.max(0, 40 - i * 3)},${Math.max(0, 6 - (i >> 1))},16`); }
    else if (l === 'q') { for (let f = 0; f < 6; f++) for (let t = 0; t < 3; t++) tx(`POL,${f},${t},${f < 2 ? 3 : f < 3 ? 1 : 0}`); tx('POL_FREIO,16,20'); }
    else if (l.startsWith('modo ')) { modo = { manual: 0, autonomo: 1, treino: 2, ia: 3 }[l.split(' ')[1]]; tx(`modo: ${['manual (Dabble)', 'autônomo (regras + TinyML)', 'treino (aprendendo por tentativa e erro)', 'IA (usa o que aprendeu)'][modo]}`); }
    else if (l === 'z') tx('aprendizado apagado');
  };
  const porta = {
    async open() {
      this.readable = new ReadableStream({ start(c) { ctl = c; setTimeout(() => tx('aprendizado: 1200 passos de treino já feitos (exploração 13%, distância do freio 16 cm)'), 200); } });
      let buf = '';
      this.writable = new WritableStream({ write(chunk) { buf += dec.decode(chunk); let i; while ((i = buf.indexOf('\n')) >= 0) { comando(buf.slice(0, i)); buf = buf.slice(i + 1); } } });
    },
    async close() { clearInterval(timer); }, async setSignals() {},
  };
  Object.defineProperty(navigator, 'serial', { value: { requestPort: async () => porta }, configurable: true });
};

let falhas = 0;
const confere = (nome, cond, detalhe = '') => { if (!cond) falhas++; console.log((cond ? 'ok   ' : 'ERRO ') + nome + (detalhe ? ' (' + detalhe + ')' : '')); };

(async () => {
  const b = await chromium.launch();
  const nova = async (init) => {
    const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
    p.erros = [];
    p.on('console', (m) => { if (m.type() === 'error') p.erros.push(m.text()); });
    p.on('pageerror', (e) => p.erros.push(e.message));
    p.on('dialog', (d) => d.accept());
    if (init) await p.addInitScript(init);
    await p.goto(url);
    return p;
  };

  // 1) demonstração
  let p = await nova();
  confere('a página abre sem erros', p.erros.length === 0, p.erros.join('; '));
  await p.click('#btn-demo'); await p.click('[data-vel="200"]'); await p.waitForTimeout(5000);
  let r = await p.evaluate(() => ({ passos: PAINEL.S.passos, blocos: PAINEL.S.blocos.length, ritmo: PAINEL.S.ritmo, pol: PAINEL.S.politica ? Object.keys(PAINEL.S.politica).length : 0, eta: document.getElementById('s-eta').textContent, modo: PAINEL.S.modo }));
  confere('demonstração: o treino avança', r.passos > 1000 && r.modo === 2, 'passos ' + r.passos);
  confere('demonstração: os blocos da curva de aprendizado aparecem', r.blocos >= 10, r.blocos + ' blocos');
  confere('demonstração: o ritmo é medido', r.ritmo > 0.5 && r.ritmo < 10, 'ritmo ' + (r.ritmo && r.ritmo.toFixed(2)) + ' passos/s');
  confere('demonstração: o que ele aprendeu (18 quadrados)', r.pol === 18);
  confere('demonstração: o tempo restante é mostrado', r.eta !== '–' && r.eta !== '', r.eta);
  // a estimativa bate com a conta: (meta - passos) / ritmo
  const est = await p.evaluate(() => { const S = PAINEL.S; S.cfgCarrinho = { meta_passos: 3000 }; S.cfg.meta_passos = 3000; return { conta: Math.max(0, 3000 - S.passos) / S.ritmo, painel: null }; });
  confere('a estimativa de tempo usa o ritmo medido', est.conta >= 0);
  confere('demonstração: sem erros no console', p.erros.length === 0, p.erros.join('; '));
  await p.close();

  // 2) as contas da configuração
  p = await nova();
  await p.fill('#f-meta_passos', '6000'); await p.fill('#f-eps_tau', '1000');
  r = await p.evaluate(() => ({ total: document.getElementById('e-total').textContent, faltam: document.getElementById('e-faltam').textContent, epsFim: document.getElementById('e-eps-fim').textContent, tpp: PAINEL.tempoPorPasso().v }));
  const esperado6000 = 6000 * r.tpp;
  confere('a meta de passos muda o tempo estimado', r.total === (await p.evaluate((s) => PAINEL.fmtTempo(s), esperado6000)), r.total);
  confere('exploração ao chegar na meta = fórmula', r.epsFim === Math.round((0.05 + 0.25 * Math.exp(-6000 / 1000)) * 100) + '%', r.epsFim);
  await p.selectOption('#presets', 'rapido');
  r = await p.evaluate(() => ({ meta: document.getElementById('f-meta_passos').value, tau: document.getElementById('f-eps_tau').value }));
  confere('as receitas de treino preenchem o formulário', r.meta === '1500' && r.tau === '600', JSON.stringify(r));
  await p.close();

  // 3) USB (porta falsa)
  p = await nova(portaFalsa);
  await p.click('#btn-usb'); await p.waitForTimeout(4200);
  r = await p.evaluate(() => ({ fonte: PAINEL.S.fonte, enviados: window.__enviados.slice(), margemMin: PAINEL.S.cfgCarrinho && PAINEL.S.cfgCarrinho.margem_min, blocos: PAINEL.S.blocos.length, pol: PAINEL.S.politica ? Object.keys(PAINEL.S.politica).length : 0, passos: PAINEL.S.passos }));
  confere('USB: conecta e pede telemetria, ajustes, histórico e política', r.fonte === 'usb' && JSON.stringify(r.enviados) === JSON.stringify(['painel 1', 'cfg?', 'e', 'q']), JSON.stringify(r.enviados));
  confere('USB: lê os ajustes do carrinho', r.margemMin === 14);
  confere('USB: recupera a curva de aprendizado do histórico (comando e)', r.blocos === 12, r.blocos + ' blocos');
  confere('USB: lê o que ele aprendeu (comando q)', r.pol === 18);
  await p.fill('#f-meta_passos', '1500');
  await p.click('#btn-iniciar'); await p.waitForTimeout(2500);
  r = await p.evaluate(() => ({ modo: PAINEL.S.modo, enviados: window.__enviados.slice(-12) }));
  confere('USB: "Iniciar treino" manda os ajustes e depois o modo treino', r.enviados.includes('cfg meta_passos 1500') && r.enviados[r.enviados.length - 1] === 'modo treino' && r.modo === 2, JSON.stringify(r.enviados));
  await p.click('#btn-parar'); await p.waitForTimeout(400);
  confere('USB: "Parar" volta ao modo manual', (await p.evaluate(() => PAINEL.S.modo)) === 0);
  await p.click('#btn-zerar'); await p.waitForTimeout(300);
  confere('USB: "Apagar aprendizado" manda z (depois de confirmar)', (await p.evaluate(() => window.__enviados)).includes('z'));
  await p.fill('#cmd', 'cfg?'); await p.press('#cmd', 'Enter'); await p.waitForTimeout(300);
  confere('USB: o campo de comando avançado envia a linha', (await p.evaluate(() => window.__enviados.filter((x) => x === 'cfg?').length)) >= 2);
  await p.click('#btn-fechar'); await p.waitForTimeout(300);
  confere('USB: desconectar atualiza o estado', (await p.evaluate(() => document.getElementById('status-txt').textContent)) === 'Desconectado');
  confere('USB: sem erros no console', p.erros.length === 0, p.erros.join('; '));
  await p.close();

  // 4) navegador sem Web Serial
  p = await nova(() => { delete Navigator.prototype.serial; });  // como o Firefox e o Safari: a propriedade não existe
  r = await p.evaluate(() => ({ aviso: !document.getElementById('aviso').hidden, desabilitado: document.getElementById('btn-usb').disabled }));
  confere('sem Web Serial: avisa e desabilita o botão de conectar, mas a demonstração continua', r.aviso && r.desabilitado);
  await p.close();

  await b.close();
  console.log(falhas ? `\n${falhas} verificação(ões) falharam` : '\no painel está certo');
  process.exit(falhas ? 1 : 0);
})();
