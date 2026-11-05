-- 1. regiões que mais choveram
SELECT r.nome, ROUND(SUM(f.chuva_mm), 1) AS mm
FROM workspace.gs.fato_chuva f JOIN workspace.gs.dim_regiao r USING (regiao_id)
GROUP BY r.nome ORDER BY mm DESC;

-- 2. horas de risco alto por região
SELECT r.nome, COUNT(*) AS horas_alto
FROM workspace.gs.fato_chuva f JOIN workspace.gs.dim_regiao r USING (regiao_id)
WHERE f.risco = 'alto' GROUP BY r.nome ORDER BY horas_alto DESC;

-- 3. chuva média por hora do dia
SELECT t.hora, ROUND(AVG(f.chuva_mm), 2) AS media_mm
FROM workspace.gs.fato_chuva f JOIN workspace.gs.dim_tempo t USING (data_hora)
GROUP BY t.hora ORDER BY t.hora;

-- 4. dias com mais chuva
SELECT t.data, ROUND(SUM(f.chuva_mm), 1) AS mm
FROM workspace.gs.fato_chuva f JOIN workspace.gs.dim_tempo t USING (data_hora)
GROUP BY t.data ORDER BY mm DESC;

-- 5. impacto: leituras do robô com umidade alta em horas de risco
SELECT COUNT(*) AS leituras_confirmadas
FROM workspace.gs.fato_leitura_robo l
JOIN workspace.gs.fato_chuva f ON f.regiao_id = l.regiao_id AND f.data_hora = l.data_hora
WHERE l.umidade_pct >= 60 AND f.risco IN ('alto', 'medio');
